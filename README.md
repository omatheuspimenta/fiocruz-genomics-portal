Install the required packages using conda env file:
```bash
conda env create -f environment.yml
```

Init the conda env
```bash
conda activate gnomad-toolbox
```

To run the app, use the command:
```bash
streamlit run code/app.py
```

Troubleshooting

In cases of Java heap memory error, export the following environment variables:

```bash
export SPARK_EXECUTOR_MEMORY=16G
export SPARK_DRIVER_MEMORY=16G
```

Change “16G” to the desired value.
