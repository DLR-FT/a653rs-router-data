{
  description = "master thesis data";

  inputs.flake-utils.url = "github:numtide/flake-utils";
  inputs.devshell.url = "github:numtide/devshell";

  outputs = { self, devshell, nixpkgs, flake-utils, ... }@inputs:
    flake-utils.lib.eachSystem [ "x86_64-linux" ] (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [
            devshell.overlays.default
          ];
        };
        pythonPackages = p: with p; [
          black
          poetry
          python-lsp-server
        ];
        python = pkgs.python3.withPackages pythonPackages;
      in
      {
        formatter = nixpkgs.nixpkgs-fmt;
        devShells.master-thesis = 
         pkgs.devshell.mkShell {
            name = "master-thesis-devshell";
            packages = with pkgs; [
              python
            ];
            commands = [ ];
        };
        devShells.default = self.devShells.${system}.master-thesis;
      });
}
