{
  description = "Development environment and container builder for deploy-hugo-gh-th";
  inputs.nixpkgs.url = "nixpkgs/nixos-22.05";

  outputs = { self, nixpkgs }:
    let
      pkgs = import nixpkgs {
        system = "x86_64-linux";
      };

      zola_pkgs = import
        (builtins.fetchGit {
          # This comes from https://lazamar.co.uk/nix-versions/?channel=nixos-22.05&package=zola
          # TODO la versione 0.14 è probabilmente breaking per i vari path, attenzione
          name = "zola-0_12_2-pkgs";
          url = "https://github.com/NixOS/nixpkgs/";
          ref = "refs/heads/nixos-22.05";
          rev = "d815581d9820503e345bc99dea0a048abc06bc63";
        })
        {
          # This is necessary because builtins.currentSystem cannot be
          # accessed in pure mode.
          localSystem = "x86_64-linux";
        };

      # Python environment to produce PDF files out of zola website
      python_env = pkgs.python39.withPackages (
        ps: with ps; [
          toml
          weasyprint
        ]
      );

      # This is the python application to deploy
      deploy_app = pkgs.python39Packages.buildPythonApplication {
        pname = "deploy_app";
        version = "0.2.1";
        propagatedBuildInputs = with pkgs; [
          cacert
          curl
          git
          hugo
          python39Packages.starlette
          python39Packages.toml
          python39Packages.uvicorn
          python39Packages.weasyprint
          rclone
          zola_pkgs.zola
        ];
        src = ./.;
      };
    in
    {
      devShell.x86_64-linux = pkgs.mkShell {
        buildInputs = with pkgs; [
          curl
          rclone
          zola_pkgs.zola
          python_env
        ];
      };

      # This is for github actions
      gha_image = pkgs.dockerTools.buildImage {
        # git is missing ca certificates
        runAsRoot = ''
          #!${pkgs.busybox}
          mkdir /workdir

          # This link is needed by GH actions
          mkdir -p /usr/bin
          ln -s `which tail` /usr/bin/tail
        '';
        name = "zola-build-and-rclone";
        tag = "latest";
        created = "now";
        contents = with pkgs; [
          busybox
          cacert
          curl
          rclone
          tree
          zola_pkgs.zola
          python_env
        ];
        config = {
          Env = with pkgs;[
            # We need this to have SSL certificates in place
            "GIT_SSL_CAINFO=${cacert}/etc/ssl/certs/ca-bundle.crt"
            "SSL_CERT_FILE=${cacert}/etc/ssl/certs/ca-bundle.crt"
            "SSL_CERT_DIR=${cacert}/etc/ssl/certs/"
            "CURL_CA_BUNDLE=${cacert}/etc/ssl/certs/ca-bundle.crt"
            "OPENSSL_X509_CERT_FILE=${cacert}/etc/ssl/certs/ca-bundle.crt"
          ];
          WorkingDir = "/workdir";
          Cmd = [ "${pkgs.busybox}/bin/sh" ];
        };
      };

      # This is the image to run the app without GH actions
      server_image = pkgs.dockerTools.buildImage {
        # git is missing ca certificates
        runAsRoot = ''
          #!${pkgs.busybox}
          mkdir /autopub
        '';
        name = "deploy_app";
        tag = "latest";
        created = "now";
        contents = [
          deploy_app
          pkgs.busybox
        ];
        config = {
          Env = with pkgs; [
            # We need this to have SSL certificates in place
            "GIT_SSL_CAINFO=${cacert}/etc/ssl/certs/ca-bundle.crt"
            "SSL_CERT_FILE=${cacert}/etc/ssl/certs/ca-bundle.crt"
            "SSL_CERT_DIR=${cacert}/etc/ssl/certs/"
            "CURL_CA_BUNDLE=${cacert}/etc/ssl/certs/ca-bundle.crt"
            "OPENSSL_X509_CERT_FILE=${cacert}/etc/ssl/certs/ca-bundle.crt"
          ];
          ExposedPorts = {
            "8000/tcp" = { };
          };
          WorkingDir = "/autopub";
          Cmd = [ "${deploy_app}/bin/server.py" ];
        };
      };

    };
}
