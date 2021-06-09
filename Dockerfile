FROM nixos/nix

# Prepare nix inside container
RUN nix-channel --add https://nixos.org/channels/nixpkgs-unstable nixpkgs
RUN nix-channel --update

# Install specific version of the tools
# https://lazamar.co.uk/nix-versions
RUN nix-env -i hugo-0.58.3 -f https://github.com/NixOS/nixpkgs/archive/b5b7bd6ebba2a165e33726b570d7ab35177cf951.tar.gz &&\
    nix-env -i zola-0.13.0 -f https://github.com/NixOS/nixpkgs/archive/c92ca95afb5043bc6faa0d526460584eccff2277.tar.gz &&\
    nix-env -i rclone-1.55.0 -f https://github.com/NixOS/nixpkgs/archive/c92ca95afb5043bc6faa0d526460584eccff2277.tar.gz

# Install python38, any should be fine
RUN nix-env -iA nixpkgs.git
RUN nix-env -iA nixpkgs.python38
RUN nix-env -iA nixpkgs.python38Packages.starlette
RUN nix-env -iA nixpkgs.python38Packages.uvicorn
RUN nix-env -iA nixpkgs.python38Packages.toml

# Install all the things!
ADD . /autopub/
WORKDIR /autopub
#RUN nix-env -f ./default.nix -i autopub

# Run the server
CMD nix-shell -p python38 -p python38Packages.starlette -p python38Packages.uvicorn -p python38Packages.toml --run "python3 server.py"
# 
# 
# installare versioni specifiche
# 
# nix-env -i hugo-0.58.3 -f https://github.com/NixOS/nixpkgs/archive/b5b7bd6ebba2a165e33726b570d7ab35177cf951.tar.gz
# nix-env -i zola-0.13.0 -f https://github.com/NixOS/nixpkgs/archive/c92ca95afb5043bc6faa0d526460584eccff2277.tar.gz
# nix-env -i rclone-1.55.0 -f https://github.com/NixOS/nixpkgs/archive/c92ca95afb5043bc6faa0d526460584eccff2277.tar.gz
# 
# TODO mettere ambiente python e far partire
# poi pulire se possibile...
# Click==7.0
# h11==0.8.1
# httptools==0.0.13
# starlette==0.12.9
# toml==0.10.2
# uvicorn==0.11.7
# uvloop==0.13.0
# websockets==8.0.2
