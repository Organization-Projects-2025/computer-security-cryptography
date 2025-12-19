from dataclasses import dataclass
import torch

@dataclass
class Args:
    # model / data config
    image_size_train = 256
    image_size_test_single = 256
    image_size_test_multiple = 256

    # SINGLE secret image
    num_secret = 1          # IMPORTANT: must be 1 for your checkpoint

    # optimizer config (not really used in GUI, but kept)
    lr = 2e-4
    warm_up_epoch = 20
    warm_up_lr_init = 5e-6

    # dataset (paths only needed if you train / run their test scripts)
    DIV2K_path = '/home/whq135/dataset'
    single_batch_size = 12
    multi_batch_szie = 8
    multi_batch_iteration = (num_secret + 1) * 8
    test_multi_batch_size = num_secret + 1

    epochs = 6000
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

    val_freq = 10
    save_freq = 200
    train_next = 0

    # MODEL VARIANT: SMALL
    use_model = 'StegFormer-S'   # MUST be S for [8, 6, 3, 3] embedding

    # not used by model directly, but kept for compatibility
    input_dim = 3

    # training strategy
    norm_train = 'clamp'
    output_act = None

    # original training paths (not used by GUI)
    path = '/home/whq135/code/StegFormer'
    model_name = 'StegFormer-S_single'   # just a name; GUI uses your .pt directly
