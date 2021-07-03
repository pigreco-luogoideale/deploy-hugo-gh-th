{ pkgs ? import <nixpkgs> {} }:
with pkgs;
let 
  my_program = python38Packages.buildPythonApplication {
    pname = "my_program";
    version = "0.0.1";
    propagatedBuildInputs = [
      git
      hugo
      python38Packages.starlette
      python38Packages.toml
      python38Packages.uvicorn
      python38Packages.weasyprint
      rclone
      zola
    ];
    src = ./.;
  };
in {
  software = my_program;

  image = dockerTools.buildImage {
    name = "my_server";
    tag = "latest";
    created = "now";
    contents = [ my_program ];
    config.Cmd = [ "${my_program}/bin/server.py" ];
  };
}
