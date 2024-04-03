{
  description = "PyCIEMSS Dev FHS Environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    let
    in
      flake-utils.lib.eachDefaultSystem (
        system:
          let
            pkgs = import nixpkgs { inherit system; };
          in rec {
              packages = { };
              devShell  = pkgs.mkShell {
                name = "python-fhs-env";
                buildInputs = [
                  pkgs.pkg-config
                  pkgs.python3Packages.cython

                  pkgs.xorg.libX11
                  pkgs.stdenv.cc.cc.lib
                  pkgs.zlib
                  pkgs.libzip
                  pkgs.libGL
                  # pkgs.opencl-headers
                  pkgs.ocl-icd
                  pkgs.openssl
                  pkgs.mtdev
                  pkgs.mesa
                  pkgs.autoPatchelfHook

                  pkgs.firefox

                  pkgs.python3
                  pkgs.poetry
                  pkgs.python3Packages.venvShellHook
                ];
                # propagatedBuildInputs = [
                # ];
                packages = [
                ];

                venvDir = "./.venv";
                postVenvCreation = ''
                  unset SOURCE_DATE_EPOCH
                  autoPatchelf ./.venv
                '';
                postShellHook = ''
                  unset SOURCE_DATE_EPOCH
                  export LD_LIBRARY_PATH=${pkgs.openssl.out}/lib:${pkgs.libzip}/lib:${pkgs.ocl-icd}/lib:${pkgs.libGL}/lib:${pkgs.mtdev}/lib:${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH
                '';
                preferLocalBuild = true;
              };
            }
      );
}
