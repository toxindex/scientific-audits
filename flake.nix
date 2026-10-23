{
  description = "Sampled scientific audits";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  outputs = { self, nixpkgs }:
    let systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];
        each = nixpkgs.lib.genAttrs systems;
        python = system: (import nixpkgs { inherit system; }).python3.withPackages (p: [ p.rdflib p.requests p.google-auth p.defusedxml p.pyshacl ]);
    in {
      packages = each (system: let pkgs = import nixpkgs { inherit system; }; in {
        linkml-check = pkgs.writeShellScriptBin "linkml-check" ''
          unset PYTHONPATH PYTHONHOME
          export UV_PROJECT_ENVIRONMENT="''${XDG_CACHE_HOME:-$HOME/.cache}/toxindex-linkml-${builtins.hashString "sha256" (builtins.readFile ./linkml/uv.lock)}"
          exec ${pkgs.uv}/bin/uv run --frozen --project ${self}/linkml python ${self}/linkml_check.py "$@"
        '';
        linkml-tests = pkgs.writeShellScriptBin "linkml-tests" ''
          unset PYTHONPATH PYTHONHOME
          export UV_PROJECT_ENVIRONMENT="''${XDG_CACHE_HOME:-$HOME/.cache}/toxindex-linkml-${builtins.hashString "sha256" (builtins.readFile ./linkml/uv.lock)}"
          exec ${pkgs.uv}/bin/uv run --frozen --project ${self}/linkml python ${self}/tests/test_linkml_check.py
        '';
        default = pkgs.writeShellScriptBin "scientific-audits" ''exec ${python system}/bin/python ${self}/audits.py "$@"'';
      });
      devShells = each (system: { default = (import nixpkgs { inherit system; }).mkShell { packages = [ (python system) ]; }; });
      apps = each (system: { linkml-tests = { type = "app"; program = "${self.packages.${system}.linkml-tests}/bin/linkml-tests"; }; linkml-check = { type = "app"; program = "${self.packages.${system}.linkml-check}/bin/linkml-check"; }; default = { type = "app"; program = "${self.packages.${system}.default}/bin/scientific-audits"; }; });
      checks = each (system: let pkgs = import nixpkgs { inherit system; }; in {
        tests = pkgs.runCommand "scientific-audits-tests" {} ''
          export PYTHONDONTWRITEBYTECODE=1
          ${python system}/bin/python ${self}/tests/test_audits.py
          touch $out
        '';
      });
    };
}
