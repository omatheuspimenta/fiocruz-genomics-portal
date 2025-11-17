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

- In cases of Java heap memory error, export the following environment variables:

```bash
  export SPARK_EXECUTOR_MEMORY=16G
  export SPARK_DRIVER_MEMORY=16G
```

  Change “16G” to the desired value.

- When using the notebook and facing memory issues, add the following to the `init` method:

```python
  hl.init(spark_conf={
        'spark.driver.memory': '320g',
        'spark.executor.memory': '320g',
        'spark.driver.maxResultSize': '100g',
        'spark.kryoserializer.buffer.max': '2047G'
    })
```

  Change the values as needed.

- Error communicating with elastic search conteiner

  1. find the container IP

      `docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <CONTAINER_ID>`

  2. change the `es_host` variable using the previous command output and add config option

  ```python
  es_host = "<CONTAINER_IP>"
  es_port = 9200

  hl.export_elasticsearch(
      ht,
      host=es_host,
      port=es_port,
      index="fiocruz_variants",
      index_type="_doc",
      block_size=1000,
      config={
          "es.nodes.wan.only": "true"   # needed to acces the container using the IP
      }
  )
  ```

