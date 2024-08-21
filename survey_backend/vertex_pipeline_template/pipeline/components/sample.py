"""
This script is used for testing changes to the package template, and for showcasing how to define Vertex components. Delete from your package.
These are custom components, using Google-managed components where possible is recommended:
https://cloud.google.com/vertex-ai/docs/pipelines/gcpc-list

Certain data types e.g. dataframes aren't compatible with kubeflow (kfp) pipelines, and have to be exchanged using kfp Artifacts:
https://www.kubeflow.org/docs/components/pipelines/v2/data-types/artifacts/
Artifacts are always treated as parameters, and cannot be returned by a kfp component.
"""
import pandas as pd

from kfp import dsl
from kfp.dsl import Input, Output, Dataset

@dsl.component(packages_to_install="random2==1.0.2") # dependency versions can be specified
def generate_multiplier() -> int:
    import random
    import logging
    
    random_num = random.randint(0,10)
    logging.info(f"Multiplier generated: {random_num}")

    return random_num


@dsl.component(packages_to_install="pandas") # use latest version of pandas 
def create_dataframe(sample_data: Output[Dataset]):
    import pandas as pd
    import logging

    sample_data = pd.DataFrame([
        {'label': 'test_row_1', 'value': 1},
        {'label': 'test_row_2', 'value': 2},
        {'label': 'test_row_3', 'value': 3}
        ])
    
    sample_data.to_csv('temp/sample_data.csv', index=False)
    sample_data.uri = 'temp/sample_data.csv' # replace with GCS writing of artifacts once GCS resources initialised
    
    logging.info(f"Sample dataframe generated:\n{sample_data}")


@dsl.component
def append_column(sample_data: Input[Dataset], transformed_data: Output[Dataset]):
    import logging
    
    transformed_data = sample_data
    transformed_data['letter'] = ['a', 'b', 'c']

    logging.info(f"Sample dataframe updated:\n{sample_data}")


@dsl.component
def apply_multiplier(transformed_data: Input[Dataset], multiplier: int):
    import logging

    logging.info(f"Original sample data:\n{transformed_data}")
    logging.info(f"Multiplying value column by {multiplier}")

    transformed_data['value'] = list(map(lambda val: val * multiplier, transformed_data['value']))

    logging.info(f"Transformed sample data:\n{transformed_data}")
    logging.info("Pipeline run completed.")
