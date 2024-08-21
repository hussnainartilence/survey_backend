"""
This script is used exclusively for testing changes to the package template. Delete from your package.
"""
from kfp.v2.dsl import Dataset

from ..sample import generate_multiplier, create_dataframe, append_column, apply_multiplier

# Define unit tests for the components
def test_generate_multiplier():
    # Call the generate_multiplier component
    multiplier = generate_multiplier()

    # Assert that the multiplier is an integer between 0 and 10
    assert isinstance(multiplier, int)
    assert 0 <= multiplier <= 10

def test_create_dataframe():
    # Create a mock output dataset object
    sample_data = Dataset(name='sample_data', description='Sample dataset', uri='gs://path/to/sample_data.csv')

    # Call the create_dataframe component
    create_dataframe(sample_data)

    # Assert that the sample dataframe is generated correctly
    # You can add assertions based on the expected output dataframe

def test_append_column():
    # Create mock input and output dataset objects
    input_data = Dataset(name='input_data', description='Input dataset', uri='gs://path/to/input_data.csv')
    transformed_data = Dataset(name='transformed_data', description='Transformed dataset', uri='gs://path/to/transformed_data.csv')

    # Call the append_column component
    append_column(input_data, transformed_data)

    # Assert that the column is appended correctly to the input dataframe
    # You can add assertions based on the expected output dataframe

def test_apply_multiplier():
    # Create mock input dataset object and multiplier
    transformed_data = Dataset(name='transformed_data', description='Transformed dataset', uri='gs://path/to/transformed_data.csv')
    multiplier = 2

    # Call the apply_multiplier component
    apply_multiplier(transformed_data, multiplier)

    # Assert that the values in the 'value' column are multiplied by the multiplier
    # You can add assertions based on the expected output dataframe