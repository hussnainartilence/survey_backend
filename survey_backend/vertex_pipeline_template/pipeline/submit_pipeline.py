from google.cloud import aiplatform

import logging

if __name__ == '__main__':
    project = "Placeholder, replace with env variable"
    location = "us-central1" 

    pipeline_name = "test-pipeline"
    pipeline_yaml_path = "gs://my-bucket/pipeline.yaml" # update to reflect changes to compile_pipeline 
    
    client = aiplatform.gapic.PipelineServiceClient(client_options={"api_endpoint": f"{location}-aiplatform.googleapis.com"})
    logging.info("AI Platform Client initialized")

    response = client.upload_pipeline(
        parent=f"projects/{project}/locations/{location}",
        pipeline=pipeline_yaml_path # update to include read step
        )
    
    logging.info("Pipeline submitted:", response)