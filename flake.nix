{
  description = "master thesis data";

  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixpkgs-unstable";
  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.poetry2nix = {
    url = "github:nix-community/poetry2nix";
  };

  outputs = { self, nixpkgs, flake-utils, poetry2nix, ... }@inputs:
    flake-utils.lib.eachSystem [ "x86_64-linux" ] (system:
      let
        # see https://github.com/nix-community/poetry2nix/tree/master#api for more functions and examples.
        inherit (poetry2nix.legacyPackages.${system}) mkPoetryApplication defaultPoetryOverrides;
        pkgs = import nixpkgs { inherit system; };
        myAppEnv = pkgs.poetry2nix.mkPoetryEnv {
          projectDir = ./.;
          editablePackageSources = {
            my-app = ./master_thesis_data;
          };
          overrides = defaultPoetryOverrides.extend
            (self: super: {
              pathspec = super.pathspec.overridePythonAttrs
                (
                  old: {
                    buildInputs = (old.buildInputs or [ ]) ++ [ super.flit-core ];
                  }
                );
            });
        };
        preCommitHook = pkgs.runCommand "pre-commit-hook"
          {
            nativeBuildInputs = [ pkgs.nixpkgs-fmt myAppEnv ];
          } ''
          nixpkgs-fmt --check ${./.}
          black --check ${./.}
          mypy ${./.}
        '';
      in
      {
        packages = {
          master-thesis-data = mkPoetryApplication { projectDir = self; };
          default = self.packages.${system}.master-thesis-data;
        };
        formatter = pkgs.nixpkgs-fmt;
        devShells.default = myAppEnv.env.overrideAttrs (oldAttrs: {
          buildInputs = (oldAttrs.buildInputs or [ ]) ++ [ pkgs.poetry pkgs.python3 ];
        });
        checks.default = preCommitHook;
      });
}
