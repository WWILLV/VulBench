# -*- coding: UTF-8 -*-
__author__ = 'WILL_V'

import logging
import docker
import time
import os
import tarfile
import io
import utils


class DockerHandle:

    def __init__(self):
        """
        DockerHandle class to manage Docker containers.
        """
        try:
            self.client = docker.from_env()
        except Exception as e:
            logging.error(e)

    def get_all_containers(self):
        """
        Get all Docker containers.
        :return: List of all Docker containers.
        """
        return self.client.containers.list(all=True)

    def get_images(self, image_name='', all=False):
        """
        Get Docker images.
        :param image_name: Name of the Docker image.
        :param all: If True, return all images, otherwise return only running images.
        :return: List of Docker images.
        """
        try:
            if all:
                return self.client.images.list(all=True)
            else:
                return self.client.images.list(name=image_name)
        except Exception as e:
            logging.error(f"Error retrieving images: {e}")
            return []

    def get_image_by_container(self, container_id):
        """
        Get the Docker image used by a specific container.
        :param container_id: ID of the Docker container.
        :return: Docker image object.
        """
        try:
            container = self.get_container(container_id)
            return container.image
        except Exception as e:
            logging.error(f"Error retrieving image for container {container_id}: {e}")
            return None

    def get_container(self, container_id):
        """
        Get a specific Docker container by its ID.
        :param container_id: ID of the Docker container.
        :return: Docker container object.
        """
        return self.client.containers.get(container_id)

    def containers_filter(self, filters=None):
        """
        Filter Docker containers based on given criteria.
        :param filters: Dictionary of filters to apply.
        :return: List of filtered Docker containers.
        """
        try:
            if filters is None:
                filters = {}
            return self.client.containers.list(all=True, filters=filters)
        except Exception as e:
            logging.error(f"Error filtering containers: {e}")
            return []

    def get_container_by_name(self, container_name):
        """
        Get a specific Docker container by its name.
        :param container_name: Name of the Docker container.
        :return: Docker container object.
        """
        try:
            return self.client.containers.get(container_name)
        except Exception as e:
            logging.error(f"Error retrieving container by name {container_name}: {e}")
            return None

    def get_container_vulbench(self, container_name="vulbench") -> list:
        """
        Get Docker containers of vulbench.
        :param container_name: If specified, filter by container name.
        :return: All Docker container objects of vulbench or filtered by name.
        """
        try:
            container_name = container_name.strip().lower()
            if container_name == '':
                container_name = 'vulbench'
            all_containers = self.get_all_containers()
            containers = []
            for container in all_containers:
                if container.name.lower().startswith(container_name):
                    containers.append(container)
            return containers
        except Exception as e:
            logging.error(f"Error retrieving vulbench containers: {e}")
            return []

    def get_image_vulbench(self, image_name="vulbench") -> list:
        """
        Get Docker images of vulbench.
        :param image_name: If specified, filter by image name.
        :return: All Docker image objects of vulbench or filtered by name.
        """
        try:
            image_name = image_name.strip().lower()
            if image_name == '':
                image_name = 'vulbench'
            all_images = self.get_images(all=True)
            images = []
            for image in all_images:
                if image.tags and any(tag.lower().startswith(image_name) for tag in image.tags):
                    images.append(image)
            return images
        except Exception as e:
            logging.error(f"Error retrieving vulbench images: {e}")
            return []

    def status(self, container_id):
        """
        Get the status of a specific Docker container.
        :param container_id: ID of the Docker container.
        :return: Dictionary containing all status statistics.
        """
        try:
            cs = self.get_container(container_id).stats(stream=False)
            if 'error' in cs:
                logging.error(f"Error retrieving status for container {container_id}: {cs['error']}")
                return None
            cpu_usage = cs.get('cpu_stats', {}).get('cpu_usage', {})
            cpuDelta = cs["cpu_stats"]["cpu_usage"]["total_usage"] - cs["precpu_stats"]["cpu_usage"]["total_usage"]
            systemDelta = cs["cpu_stats"]["system_cpu_usage"] - cs["precpu_stats"]["system_cpu_usage"]
            cpuPercent = (cpuDelta / systemDelta) * (cs["cpu_stats"]["online_cpus"]) * 100
            cpuPercent = int(cpuPercent)
            memory_usage = cs.get('memory_stats', {}).get('usage', 0)
            memPercent = (memory_usage / cs.get('memory_stats', {}).get('limit', 1)) * 100
            return {
                'container_id': container_id,
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'cpu_percent': cpuPercent,
                'mem_percent': memPercent,
                'all_status': cs
            }
        except Exception as e:
            logging.error(f"Error retrieving status for container {container_id}: {e}")
            return None

    def run_by_image(self, image=None, name='', tag='latest', patched=False, run_kwargs=None):
        """
        Build and run a Docker container from an existing image.
        :param image: Docker image object.
        :param name: Name for the Docker container.
        :param tag: Tag for the Docker image.
        :param patched: If True, add `patched` suffix to the container name.
        :param run_kwargs: Additional keyword arguments for client.containers.run.
        :return: The created container object.
        """
        try:
            if image is None:
                raise Exception("Image cannot be empty.")
            if name == '':
                image_name = image.tags[0].split(':')[0] if image.tags else 'vulbench'
                if image_name.startswith('vulbench'):
                    name = f"{image_name}_{time.strftime('%Y%m%d%H%M%S')}"
                else:
                    name = f"vulbench_{image_name}_{time.strftime('%Y%m%d%H%M%S')}"
                if patched:
                    name += '_patched'
            img_name, img_tag = image.tags[0].split(':') if image.tags else (image.name, tag)
            logging.info(f"Trying to run container from image {img_name}:{img_tag}")
            image = self.client.images.get(f"{img_name}:{img_tag}")
            container = self.client.containers.run(
                image=image,
                detach=True,  # -d
                name=name,
                stdin_open=True,  # -i
                tty=True,  # -t
                **(run_kwargs if run_kwargs else {})
            )
            return container
        except Exception as e:
            logging.error(f"Error running container from image {image.tags}: {e}")
            return None

    def run_by_dockerfile(self, dockerfile_path, image_name, name='', tag='latest', run_kwargs=None):
        """
        Build and run a Docker container from a Dockerfile.
        :param dockerfile_path: Path to the Dockerfile.
        :param image_name: Name of the Docker image to build.
        :param name: Name for the Docker container.
        :param tag: Tag for the Docker image.
        :param run_kwargs: Additional keyword arguments for client.containers.run.
        :return: The created container object.
        """
        try:
            if name == '':
                if image_name.startswith('vulbench'):
                    name = f"{image_name}_{time.strftime('%Y%m%d%H%M%S')}"
                else:
                    name = f"vulbench_{image_name}_{time.strftime('%Y%m%d%H%M%S')}"
            build_dir = os.path.dirname(dockerfile_path)
            dockerfile_name = os.path.basename(dockerfile_path)
            logging.info(f"Trying to build and run container from {dockerfile_path} with image {image_name}:{tag}")
            image = self.client.images.build(
                path=build_dir,
                dockerfile=dockerfile_name,
                tag=f"{image_name}:{tag}",
                labels={"maintainer": "vulbench"},
                rm=True,
                forcerm=True
            )[0]
            container = self.client.containers.run(
                image=image,
                detach=True,  # -d
                name=name,
                stdin_open=True,  # -i
                tty=True,  # -t
                **(run_kwargs if run_kwargs else {})
            )
            return container
        except Exception as e:
            logging.error(f"Error building or running container from {dockerfile_path}: {e}")
            return None

    def container_copy(self, container_id, src_path, dest_path):
        """
        Copy files from the host to a Docker container.
        :param container_id: ID of the Docker container.
        :param src_path: Source path on the host.
        :param dest_path: Destination path in the container.
        :return: None
        """
        try:
            container = self.get_container(container_id)
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode='w') as tar:
                tar.add(src_path, arcname=os.path.basename(dest_path))
            tar_stream.seek(0)
            container.put_archive(os.path.dirname(dest_path), tar_stream)
            logging.info(f"Copied {src_path} to {container_id}:{dest_path}")
        except Exception as e:
            logging.error(f"Error copying files to container {container_id}: {e}")

    def get_files_from_container(self, container_id, src_path='/vulbench/vb_poc_result.json', dest_path=''):
        """
        Get files from a Docker container to the host.
        :param container_id: ID of the Docker container.
        :param src_path: Source path in the container.
        :param dest_path: Destination path on the host.
        :return: destination path where files are copied.
        """
        try:
            if dest_path == '':
                dest_path = os.path.join(utils.get_workspace(), container_id, os.path.basename(src_path))
            container = self.get_container(container_id)
            tar_stream_gen, stat = container.get_archive(src_path)
            tar_bytes = b''.join(tar_stream_gen)
            tar_stream = io.BytesIO(tar_bytes)
            with tarfile.open(fileobj=tar_stream, mode='r') as tar:
                tar.extractall(path=dest_path)
            logging.info(f"Copied files from {container_id}:{src_path} to {dest_path}")
            return dest_path
        except Exception as e:
            logging.error(f"Error getting files from container {container_id}: {e}")
            return None

    def container_exec(self, container_id, command):
        """
        Execute a command in a Docker container.
        :param container_id: ID of the Docker container.
        :param command: Command to execute in the container.
        :return: Output of the command execution.
        """
        try:
            container = self.get_container(container_id)
            exec_result = self.client.api.exec_create(container.id, command)
            output = self.client.api.exec_start(exec_result['Id'])
            logging.info(f"Executed command '{command}' in container {container_id}")
            return output.decode('utf-8')
        except Exception as e:
            logging.error(f"Error executing command in container {container_id}: {e}")
            return None

    def container_kill(self, container_id):
        """
        Kill a Docker container.
        :param container_id: ID of the Docker container.
        :return: None
        """
        try:
            container = self.get_container(container_id)
            container.kill()
            logging.warning(f"Killed container {container_id}")
        except Exception as e:
            logging.error(f"Error killing container {container_id}: {e}")

    def container_remove(self, container_id, timeout=10):
        """
        Remove a Docker container.
        :param container_id: ID of the Docker container.
        :param timeout: Timeout in seconds to wait for the container to exit.
        :return: None
        """
        try:
            container = self.get_container(container_id)
            if container.status != 'exited':
                container.kill()
                for _ in range(timeout):
                    container.reload()
                    if container.status == 'exited':
                        break
                    time.sleep(1)
            container.remove(force=True)
            logging.warning(f"Removed container {container_id}")
        except Exception as e:
            logging.error(f"Error removing container {container_id}: {e}")

    def image_remove(self, image_name, timeout=10):
        """
        Remove a Docker image.
        :param image_name: Name of the Docker image.
        :param timeout: Timeout in seconds to wait for dependent containers to stop.
        :return: None
        """
        try:
            containers = self.client.containers.list(all=True, filters={'ancestor': image_name})
            for c in containers:
                self.container_remove(c.id, timeout=timeout)
            self.client.images.remove(image_name, force=True)
            logging.warning(f"Removed image {image_name}")
        except Exception as e:
            logging.error(f"Error removing image {image_name}: {e}")

    def remove_dangling_images(self, timeout=10, only_vulbench=True, image_id=''):
        """
        Remove dangling Docker images.
        :param timeout: Timeout in seconds to wait for dependent containers to stop.
        :param only_vulbench: If True, only remove dangling images related to vulbench.
        :param image_id: If specified, remove only the dangling image with this ID.
        :return: True if all vulbench dangling images were removed, False otherwise.
        """
        try:
            def get_dangling(only_vulbench=only_vulbench):
                if only_vulbench:
                    dangling = self.client.images.list(name='vulbench', all=True,
                                                       filters={'dangling': True, 'label': 'maintainer=vulbench'})
                    if not dangling:
                        logging.info("No VulBench dangling images found.")
                else:
                    dangling = self.client.images.list(filters={'dangling': True})
                    if not dangling:
                        logging.info("No dangling images found.")
                return dangling

            if image_id != '':
                try:
                    img = self.client.images.get(image_id)
                    dangling = [img]
                except Exception as e:
                    logging.error(f"Error retrieving image {image_id}: {e}")
                    dangling = []
            else:
                dangling = get_dangling(only_vulbench)

            if not dangling:
                return True
            logging.warning(f"Found {len(dangling)} dangling images to remove.")

            for img in dangling:
                containers = self.client.containers.list(all=True, filters={'ancestor': img.id})
                for c in containers:
                    self.container_remove(c.id, timeout=timeout)
                self.client.images.remove(img.id, force=True)
                logging.warning(f"Removed dangling image {img.id}")

            dangling = get_dangling(only_vulbench)

            if only_vulbench and len(dangling) != 0:
                for img in dangling:
                    try:
                        history = self.client.api.history(img.id)
                        for layer in history:
                            tags = layer.get("Tags", [])
                            if tags:
                                if any(tag.startswith("vulbench_") for tag in tags if tag):
                                    containers = self.client.containers.list(all=True, filters={'ancestor': img.id})
                                    for c in containers:
                                        self.container_remove(c.id, timeout=timeout)
                                    self.client.images.remove(img.id, force=True)
                                    logging.warning(f"Removed VulBench-related dangling image {img.id}")
                                    break
                    except Exception as e:
                        logging.warning(f"Error checking image {img.id}: {e}")

            return len(get_dangling(only_vulbench)) == 0
        except Exception as e:
            logging.error(f"Error removing dangling images: {e}")
            return False
