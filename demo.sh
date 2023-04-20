# Generate spiral demo images by using a trained KiloOSF model
DATASET=chicken_kart
python run_nerf.py cfgs/paper/finetune/$DATASET.yaml -rcfg cfgs/render/demo.yaml 
