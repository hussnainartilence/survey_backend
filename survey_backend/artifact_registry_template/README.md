(work in progress)

# Artifact Registry Template

Directory containing template structure for [Artifact Registry](https://cloud.google.com/artifact-registry/?gad_source=1&gclid=CjwKCAiAuYuvBhApEiwAzq_YiafJRIYoDVeKYrkOw9U62U20qdccSpIDWlBEtPslxXlxw22m77HiIxoCxo4QAvD_BwE&gclsrc=aw.ds) packages. Once completeted, ideally needs to be reproduced as a standalone registry (one registry per package).

Purpose of the Artifact Registry is to store re-usable code packages e.g. video utils, which could contain functions/classes related to video processing:

```
Artifact Registry
- guardrails_utils
  - video-utils
    - extact_video_text # func for extracting video sounds and converting to text 

# can be utilised within Vertex components as follows
from guardrails_utils.video-utils import extract_video_text
```

TODO:
* Set up dedicated repository for template that can be duplicated in the future. Move [actions workflow](https://github.com/projektrising/Validation_Guardrails/blob/main/.github/workflows/publish-artifact-registry-package.yml) for this to the repo. Needs to be discussed w/ team first
* Add import of test package to poetry config as an example of custom package import
* Add Artifact Registry repository as a Poetry Source e.g.
```
[tool.poetry.source]
name = "artifact-registry-utils"
url = "Artifact registry repository URL"
```