# Benchmark (PSNR, SSIM, LPIPS, render time) a trained KiloOSF model on the test set
DATASET=chicken_kart
python run_nerf.py cfgs/paper/finetune/$DATASET.yaml -rcfg cfgs/render/benchmark.yaml 
