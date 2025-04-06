locals {
  image_name_full = "${var.base_name}-${var.image_name}"
}

# # create the docker image and push it to the container registry
# # necessary to use buildx on mac os with amd-architecture to build arm images
# resource "null_resource" "docker-buildx" {
  
#     # this trigger makes sure that the script is executed every time
#   triggers = {
#     timestamp = "${timestamp()}"
#   }
  
#   provisioner "local-exec" {
#     # call buildx script
#     working_dir = "${path.module}/../docker/"
#     command = "./containerize.sh ${var.acr_login_server} ${local.image_name_full}"
#   }
# }

# # get the version dynamically from the container registry
# data "external" "version" {
#   program = ["bash", "-c", <<EOF
#     version=$(az acr repository show-tags -n ${var.acr_login_server} --repository ${local.image_name_full} --top 1 --orderby time_desc -o tsv)
#     echo "{\"version\": \"$version\"}"
#   EOF
#   ]

#   depends_on = [ null_resource.docker-buildx ]
# }