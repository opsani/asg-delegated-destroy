<!-- vim: set filetype=markdown: -->
# asg-delegated-destroy

This is a very simple HTTP server implemented in Python that includes the basic
functionality needed for a 'delegated termination' API implementation to
be used when maintaining applications running on EC2 with Opsani Skopos,
using the ec2-asg plugin.

Although it can be used unmodified, the code is meant to be a starting point for
developing your own delegated termination handler.

The server can be run directly as an executable, see the Python file for instructions.

It can also be packaged and ran as a Docker container, with the supplied
Dockerfile, e.g:

```
docker build --tag opsani/asg-delegated-destroy:latest .
```

## Deploying the server

### Deploying with Skopos

See the `skopos` subdirectory for deployment artifacts. The model includes
a quality gate that verifies that the server is responding on its API before
completing the deployment successfully.

Use the following command to deploy (from the `skopos` subdirectory):

`skopos run --wait --project ddsrv --env env.yaml model.yaml`


### Deploying with Docker

When packaged in a container, run it like this using Docker
(`-v ...` is optional, needed only if using a config file for AWS access; omit if using AWS roles):

```
docker run -v ~/.aws:/root/.aws -d -p 8000:8000 --name ddsrv opsani/asg-delegated-destroy:latest
```

WARNING: use the `docker run -p ...` option with care, it will expose the server on all of the
host's interfaces. If you will be accessing the API from another container on the same host,
don't use `-p` at all. Instead, use the container name, as given with the `--name` option above as
the hostname in the URL. Here is an example snippet of a Skopos environment config file, with the
hostname set as the container name from the command-line example above:

```
plugin_config:
	ec2-asg:
		delegated_destroy:
			uri: http://ddsrv:8000/delayed-termination
			# list of components whose instances should be handed off to the API when
			# planned for teardown, instead of being terminated immediately:
			components: [ 'name1', ... ]
```


See also the `ec2-asg` plugin documentation for details how to configure delegated destroy for your stack.