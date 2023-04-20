"""Data loader for OSF data."""

import os
import torch
import numpy as np
import imageio 
import json
import cv2

import cam_utils


trans_t = lambda t: torch.tensor([
    [1,0,0,0],
    [0,1,0,0],
    [0,0,1,t],
    [0,0,0,1]
], dtype=torch.float)

rot_phi = lambda phi: torch.tensor([
    [1,0,0,0],
    [0,np.cos(phi),-np.sin(phi),0],
    [0,np.sin(phi), np.cos(phi),0],
    [0,0,0,1]
], dtype=torch.float)

rot_theta = lambda th: torch.tensor([
    [np.cos(th),0,-np.sin(th),0],
    [0,1,0,0],
    [np.sin(th),0, np.cos(th),0],
    [0,0,0,1]
], dtype=torch.float)


def pose_spherical(theta, phi, radius):
    c2w = trans_t(radius)
    c2w = rot_phi(phi/180.*np.pi) @ c2w
    c2w = rot_theta(theta/180.*np.pi) @ c2w
    c2w = torch.Tensor(np.array([[-1,0,0,0],[0,0,1,0],[0,1,0,0],[0,0,0,1]])) @ c2w
    return c2w


def convert_cameras_to_nerf_format(anno):
    """
    Args:
        anno: List of annotations for each example. Each annotation is represented by a
            dictionary that must contain the key `RT` which is the world-to-camera
            extrinsics matrix with shape [3, 4], in [right, down, forward] coordinates.

    Returns:
        c2w: [N, 4, 4] np.float32. Array of camera-to-world extrinsics matrices in
            [right, up, backwards] coordinates.
    """
    c2w_list = []
    for a in anno:
        # Convert from w2c to c2w.
        w2c = np.array(a['RT'] + [[0.0, 0.0, 0.0, 1.0]])
        c2w = cam_utils.w2c_to_c2w(w2c)

        # Convert from [right, down, forwards] to [right, up, backwards]
        c2w[:3, 1] *= -1  # down -> up
        c2w[:3, 2] *= -1  # forwards -> back
        c2w_list.append(c2w)
    c2w = np.array(c2w_list)
    return c2w


def load_osf_data(basedir, near, far, spiral_radius, half_res=False, testskip=1,
        n_render_spiral=40, render_spiral_angles=None):
    """
    Returns:
        imgs: [H, W, 4] np.float32. Array of images in RGBA format, and normalized
            between [0, 1].
    """
    splits = ['train', 'val', 'test']
    metas = {}
    for s in splits:
        with open(os.path.join(basedir, '{}/anno.json'.format(s)), 'r') as fp:
            anno = json.load(fp)

        # Convert camera matrices into NeRF format.
        c2w = convert_cameras_to_nerf_format(anno)
        for i in range(len(anno)):
            anno[i]['c2w'] = c2w[i]

        metas[s] = anno

    all_imgs = []
    all_poses = []
    all_metadata = []
    counts = [0]
    for s in splits:
        meta = metas[s]
        imgs = []
        poses = []
        metadata = []

        if s=='train' or testskip==0:
            skip = 1
        else:
            skip = testskip

        for frame in meta[::skip]:
            fname = os.path.join(basedir, s, frame['filename'])
            imgs.append(imageio.imread(fname))  # [H, W, 4]
            poses.append(frame['c2w'])  # [4, 4]
            metadata.append(frame['light_pos'])  # [3,]

        # Normalize images, and keep all 4 channels (RGBA).
        imgs = (np.array(imgs) / 255.).astype(np.float32)  # [N, H, W, 4]

        poses = np.array(poses).astype(np.float32)  # [N, 4, 4]
        metadata = np.array(metadata).astype(np.float32)  # [N, 3]
        counts.append(counts[-1] + imgs.shape[0])
        all_imgs.append(imgs)
        all_poses.append(poses)
        all_metadata.append(metadata)

    # Create a list where each element contains example indices for each split.
    i_split = [np.arange(counts[i], counts[i+1]) for i in range(3)]
    i_split[0] = np.concatenate((i_split[0], i_split[1]))
    #i_split[2] = i_split[1]  # Make test equal to val

    imgs = np.concatenate(all_imgs, 0)  # [N, H, W, 4]
    poses = np.concatenate(all_poses, 0)  # [N, 4, 4]
    metadata = np.concatenate(all_metadata, 0)  # [N, 3]

    # Extract the height and width from the shape of the first image example.
    H, W = imgs[0].shape[:2]

    # Compute the focal length.
    focal = meta[0]['K'][0][0]

    # Render poses for generating spiral videos.
    if spiral_radius is None:
        translations = poses[:, :3, 3]  # [N, 3]
        # center = translations.mean(axis=0, keepdims=True)  # [1, 3]
        center = [0, 0, 0]  # For now hard code center to be origin.
        dists = np.linalg.norm(translations - center, axis=1)  # [N,]
        spiral_radius = np.max(dists)
    if render_spiral_angles is None:
        # If no angles are provided, simply discretize 360 degrees inot n_render_spiral.
        render_spiral_angles = np.concatenate((np.linspace(-270, 90,n_render_spiral+1)[:-1], np.linspace(-270, -270, n_render_spiral)))
    else:  # If angles are provided.
        if len(render_spiral_angles) == 1:
            # If only one angle is provided, each frame is going to be the same angle,
            # repeated by n times.
            render_spiral_angles = render_spiral_angles * n_render_spiral
        else:
            # If more than one angle is provided, then we ignore n_render_spiral and
            # simply use the provided list of angles.
            pass
    print("radius: ", spiral_radius)
    render_poses = torch.stack([pose_spherical(
            theta=angle, phi=-30.0, radius=spiral_radius) for angle in render_spiral_angles],0)  # [N, 4, 4]

    # Set the render lighting

    light_angle = [90] * n_render_spiral + [360//n_render_spiral * i + 90 for i in range(n_render_spiral)]
    light_render_pose = torch.stack([pose_spherical(  # [4, 4]
            theta=angle, phi=-30.0, radius=15.0) for angle in light_angle])

    light_pos = light_render_pose[:, :3, 3]
    render_metadata = light_pos
    if half_res:
        H = H//2
        W = W//2
        focal = focal/2.

        imgs_half_res = np.zeros((imgs.shape[0], H, W, 4))
        for i, img in enumerate(imgs):
            imgs_half_res[i] = cv2.resize(img, (H, W), interpolation=cv2.INTER_AREA)
        imgs = imgs_half_res

    return imgs, poses, render_poses, [H, W, focal], i_split, metadata, render_metadata
