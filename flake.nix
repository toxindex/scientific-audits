{
  description = "Sampled scientific audits";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  outputs = { self, nixpkgs }:
    let systems = [ "x86_64-linux" "aarch64-linux" "aarch64-darwin" "x86_64-darwin" ];
        each = nixpkgs.lib.genAttrs systems;
        python = system: (import nixpkgs { inherit system; }).python3.withPackages (p: [ p.rdflib p.requests p.google-auth p.defusedxml p.pyshacl ]);
    in {
      packages = each (system: let pkgs = import nixpkgs { inherit system; }; in {
        default = pkgs.writeShellScriptBin "scientific-audits" ''exec ${python system}/bin/python ${self}/audits.py "$@"'';
      });
      devShells = each (system: { default = (import nixpkgs { inherit system; }).mkShell { packages = [ (python system) ]; }; });
      apps = each (system: { default = { type = "app"; program = "${self.packages.${system}.default}/bin/scientific-audits"; }; });
      checks = each (system: let pkgs = import nixpkgs { inherit system; }; in {
        tests = pkgs.runCommand "scientific-audits-tests" {} ''
          export PYTHONDONTWRITEBYTECODE=1
          ${python system}/bin/python ${self}/tests/test_audits.py
          touch $out
        '';
      });
    };
}
