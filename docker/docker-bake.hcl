variable "DOCKER_REGISTRY" {
  default = "ghcr.io"
}
variable "DOCKER_ORG" {
  default = "darpa-askem"
}
variable "VERSION" {
  default = "local"
}

# ----------------------------------------------------------------------------------------------------------------------

function "tag" {
  params = [image_name, prefix, suffix]
  result = [ "${DOCKER_REGISTRY}/${DOCKER_ORG}/${image_name}:${check_prefix(prefix)}${VERSION}${check_suffix(suffix)}" ]
}

function "check_prefix" {
  params = [tag]
  result = notequal("",tag) ? "${tag}-": ""
}

function "check_suffix" {
  params = [tag]
  result = notequal("",tag) ? "-${tag}": ""
}

# ----------------------------------------------------------------------------------------------------------------------

group "prod" {
  targets = ["pyciemss-api", "pyciemss-worker"]
}

group "default" {
  targets = ["pyciemss-api-base", "pyciemss-worker-base"]
}

# ----------------------------------------------------------------------------------------------------------------------

target "_platforms" {
  platforms = ["linux/amd64", "linux/arm64"]
}

target "pyciemss-api-base" {
  context = ".."
  tags = tag("pyciemss-api", "", "")
  dockerfile = "docker/Dockerfile.api"
}

target "pyciemss-api" {
  inherits = ["_platforms", "pyciemss-api-base"]
}

target "pyciemss-worker-base" {
  context = ".."
  tags = tag("pyciemss-worker", "", "")
  dockerfile = "docker/Dockerfile.worker"
}

target "pyciemss-worker" {
  inherits = ["_platforms", "pyciemss-worker-base"]
}