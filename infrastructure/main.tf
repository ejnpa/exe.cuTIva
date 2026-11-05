terraform {
    required_providers {
        docker = {
            source="kreuzwerker/docker"
            version="~>3.0.1"
        }
    }
}

provider "docker" {
    host = "ssh://emanuel@100.89.13.43:22"
}

resource "docker_volume" "pgdata"{
    name="pgdata"
}

resource "docker_volume" "azurite_data"{
    name="azurite_data"
}

resource "docker_volume" "media_data"{
    name="media_data"
}

resource "docker_network" "webnet" {
    name="webnet"
}

resource "docker_network" "backend" {
    name="backend"
    internal=true
}