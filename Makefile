# Variables
IMAGE_NAME = shopware-reports-app
CONTAINER_NAME = shopware-reports-container

# Build the Docker image
build:
	docker build -t $(IMAGE_NAME) .

# Run the Docker container
run:
	docker run -d --name $(CONTAINER_NAME) -p 8000:8000 $(IMAGE_NAME)

# Stop the Docker container
stop:
	docker stop $(CONTAINER_NAME)

# Remove the Docker container
remove:
	docker rm $(CONTAINER_NAME)

# Build and run the Docker container
up: build run

# Stop and remove the Docker container
down: stop remove

# View the logs of the running container
logs:
	docker logs $(CONTAINER_NAME)

# Enter the running container
shell:
	docker exec -it $(CONTAINER_NAME) /bin/bash

# Clean up: stop and remove the container, and remove the image
clean: down
	docker rmi $(IMAGE_NAME)

.PHONY: build run stop remove up down logs shell clean