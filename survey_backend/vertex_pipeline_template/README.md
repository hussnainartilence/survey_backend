(work in progress)

# Vertex Pipeline Template

Directory containing template structure for deploying [Vertex Pipelines](https://cloud.google.com/vertex-ai/docs/pipelines/build-pipeline). Once completeted, ideally needs to be reproduced as a standalone registry (one registry per package).

Purpose of the template is to have a pre-set repo structure which a CI/CD template can leverage to deploy any changes to the overall pipeline, or any underlying Vertex components. Component code should all be managable within the repository itself.

Ideally, repository should be set up in a manner that any changes can also be propogated to the API endpoint - but exact nature of this is still TBD.

TODO:
* Initialise GCP resources (projects, service accounts, buckets, roles, API enablement)
* Update sample components/tests to utilise GCP for artifacts
* Update submit_pipeline to require no configuration for new projects
* Update compile_pipeline to require minimal configuration (outside of pipeline coding)
* Deploy/test sample pipeline
* Add an import from Artifact Registry to a sample component