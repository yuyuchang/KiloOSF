DATASET=chicken_kart

# Training a Vanilla NeRF as teacher model
python run_nerf.py cfgs/paper/pretrain/$DATASET.yaml

# Extracting occupancy grid from teacher model
python build_occupancy_tree.py cfgs/paper/pretrain_occupancy/$DATASET.yaml

# Distilling teacher into KiloOSF model
python local_distill.py cfgs/paper/distill/$DATASET.yaml

# Fine-tuning KiloOSF model
python run_nerf.py cfgs/paper/finetune/$DATASET.yaml
