from kfp import dsl, compiler

from components.sample import generate_multiplier, create_dataframe, append_column, apply_multiplier

# replace test pipeline with your pipeline
@dsl.pipeline(name='test-pipeline', pipeline_root='gs://my-bucket') # update to dedicated bucket per pipeline e.g. pipelines/guardrails
def test_pipeline():
    generate_multiplier_op = generate_multiplier()
    multiplier = generate_multiplier_op.output

    create_dataframe_op = create_dataframe()
    sample_data = create_dataframe_op.outputs['sample_data'].uri

    append_column_op = append_column(sample_data)
    transformed_data = append_column_op.outputs['transformed_data'].uri

    apply_multiplier(transformed_data, multiplier)


if __name__ == '__main__':
    compiler.Compiler().compile(test_pipeline, package_path='pipeline.yaml') # update to dynamically append a pipeline version based on metadata 