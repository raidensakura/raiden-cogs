`cpu.py` and `gpu.py` contains code to index specific benchmark pages for scores and output them into `cpu.json` and `gpu.json` that the cog uses for data points. The scripts themselves are independent from the cog and will need to be run externally. I only decided to include it here so I don't have to manage separate repositories and to keep things simple.

`weights.json` is pretty much self explanatory, just weight values the cog will use to determine overall score for each CPU/GPU.
