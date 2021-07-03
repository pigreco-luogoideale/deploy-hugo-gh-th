{ pkgs ? import <nixpkgs> {} }:
with pkgs;
let 
  # packages to pin specific versions using https://lazamar.co.uk/nix-versions
  zola_pkgs = import (builtins.fetchGit {
    # Descriptive name to make the store path easier to identify                
    name = "zola-0_12_2-pkgs";
    url = "https://github.com/NixOS/nixpkgs/";
    ref = "refs/heads/nixpkgs-unstable";
    rev = "559cf76fa3642106d9f23c9e845baf4d354be682";
  }) { };

  deploy_app = python38Packages.buildPythonApplication {
    pname = "deploy_app";
    version = "0.3.0";
    propagatedBuildInputs = [
      cacert
      curl
      git
      hugo
      python38Packages.starlette
      python38Packages.toml
      python38Packages.uvicorn
      python38Packages.weasyprint
      rclone
      zola_pkgs.zola
    ];
    src = ./.;
  };
in {
  package = deploy_app;

  image = dockerTools.buildImage {
    # git is missing ca certificates
    runAsRoot = ''
      #!${busybox}
      mkdir /autopub
    '';
    name = "deploy_app";
    tag = "latest";
    created = "now";
    contents = [
      deploy_app
      busybox
    ];
    config = {
      Env = [
        # We need this to have SSL certificates in place
        "GIT_SSL_CAINFO=${cacert}/etc/ssl/certs/ca-bundle.crt"
        "SSL_CERT_FILE=${cacert}/etc/ssl/certs/ca-bundle.crt"
        "SSL_CERT_DIR=${cacert}/etc/ssl/certs/"
        "CURL_CA_BUNDLE=${cacert}/etc/ssl/certs/ca-bundle.crt"
        "OPENSSL_X509_CERT_FILE=${cacert}/etc/ssl/certs/ca-bundle.crt"
      ];
      ExposedPorts = {
        "8000/tcp" = {};
      };
      WorkingDir = "/autopub";
      Cmd = [ "${deploy_app}/bin/server.py" ];
    };
  };
}
