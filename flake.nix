{
  description = "Build Debian packages in containers";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-22.11";
  inputs.poetry2nix = {
    url = "github:nix-community/poetry2nix";
    inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # see https://github.com/nix-community/poetry2nix/tree/master#api for more functions and examples.
        inherit (poetry2nix.legacyPackages.${system}) mkPoetryApplication;
        pkgs = nixpkgs.legacyPackages.${system};
        customOverrides = self: super: {
          python-debian = super.python-debian.overrideAttrs
            (old: { buildInputs = old.buildInputs ++ [ self.setuptools ]; });
        };
      in {
        packages = {
          myapp = mkPoetryApplication {
            projectDir = self;
            overrides =
              [ pkgs.poetry2nix.defaultPoetryOverrides customOverrides ];
          };
          default = self.packages.${system}.myapp;
        };

        devShells.default = pkgs.mkShell {
          packages = [ poetry2nix.packages.${system}.poetry pkgs.podman ];
        };
      });
}
