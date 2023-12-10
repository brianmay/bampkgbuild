{
  description = "Build Debian packages in containers";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
  inputs.poetry2nix = {
    url = "github:nix-community/poetry2nix";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # see https://github.com/nix-community/poetry2nix/tree/master#api for more functions and examples.
        p2n = import poetry2nix { inherit pkgs; };
        mkPoetryApplication = p2n.mkPoetryApplication;
        pkgs = nixpkgs.legacyPackages.${system};
      in {
        packages = {
          myapp = mkPoetryApplication {
            projectDir = self;
            #overrides =
            #  [ pkgs.poetry2nix.defaultPoetryOverrides customOverrides ];
            overrides = p2n.overrides.withDefaults (final: prev: {
              python-debian = prev.python-debian.overridePythonAttrs
                (oldAttrs: {
                  buildInputs = oldAttrs.buildInputs ++ [ final.setuptools ];
                });
            });
          };
          default = self.packages.${system}.myapp;
        };

        devShells.default =
          pkgs.mkShell { packages = [ pkgs.poetry pkgs.podman ]; };
      });
}
