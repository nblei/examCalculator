#!/usr/bin/python3
from docopt import docopt
from sys import argv, stderr
from functools import reduce


def conv_reuse(tile, mask):
    dim = len(tile)
    assert(dim == len(mask))
    nom = reduce(lambda x, y: x*y,
                 map(lambda x: x[0]*x[1], zip(tile, mask)),
                 1)
    denom = reduce(lambda x, y: x*y,
                   map(lambda x: x[0]+x[1]-1, zip(tile, mask)),
                   1)

    return {'Average Data Reuse for internal node': nom/denom}


def threeDit(tup):
    tx, ty, tz = tup
    for k in range(tz):
        for j in range(ty):
            for i in range(tx):
                yield (i, j, k)


def warp_divergence3d(blockDim, imgDim, warpsize):
    bx, by, bz = blockDim
    ix, iy, iz = imgDim
    nbx: int = (ix + (bx-1)) // bx
    nby: int = (iy + (by-1)) // by
    nbz: int = (iz + (bz-1)) // bz
    gridDim = (nbx, nby, nbz)
    del nbx
    del nby
    del nbz
    del bx
    del by
    del bz

    warp: int = 0
    divergence: bool = False
    inbounds: bool = False
    divcnt: int = 0
    counted: bool = False

    def is_inbounds(tidx, bidx):
        _x = bidx[0] * blockDim[0] + tidx[0]
        _y = bidx[1] * blockDim[1] + tidx[1]
        _z = bidx[2] * blockDim[2] + tidx[2]
        return (_x < imgDim[0]) and (_y < imgDim[1]) and (_z < imgDim[2])

    def block_skip(tidx, bidx):
        _x = bidx[0] * blockDim[0] * 2 + tidx[0]
        _x2 = _x + blockDim[0]
        return (_x < imgDim[0]) and (_x2 < imgDim[0])

    predicate = block_skip

    divergent_warps = []
    for bidx in threeDit(gridDim):
        for tidx in threeDit(blockDim):
            # print(img_idx, img_idy)
            if warp % warpsize == 0:
                divergence = False
                inbounds = predicate(tidx, bidx)
                counted = False
            else:
                if inbounds != predicate(tidx, bidx):
                    divergence = True
                    if divergence is True and counted is False:
                        divcnt += 1
                        counted = True
                        divergent_warps.append(warp // warpsize)
            warp += 1

    return {'Number of Divergent Warps': divcnt,
            'Divergent Warps': divergent_warps}


def warp_divergence2d(bx: int, by: int, ix: int, iy: int, ws: int):
    ''' Actually do simulation because that's easiest to program '''
    nbx: int = (ix + (bx-1)) // bx
    nby: int = (iy + (by-1)) // by
    warp: int = 0
    divergence: bool = False
    inbounds: bool = False
    divcnt: int = 0
    counted: bool = False

    def is_inbounds(_x, _y):
        return (_x < ix) and (_y < iy)

    divergent_warps = []
    for blockx in range(nbx):
        for blocky in range(nby):
            for idx in range(bx):
                for idy in range(by):
                    img_idx = blockx * bx + idx
                    img_idy = blocky * by + idy
                    # print(img_idx, img_idy)
                    if warp % ws == 0:
                        divergence = False
                        inbounds = is_inbounds(img_idx, img_idy)
                        counted = False
                    else:
                        if inbounds != is_inbounds(img_idx, img_idy):
                            divergence = True
                            if divergence is True and counted is False:
                                divcnt += 1
                                counted = True
                                divergent_warps.append(warp // ws)
                    warp += 1

    return {'Number of Divergent Warps': divcnt,
            'Divergent Warps': divergent_warps}


def print_results(res):
    for key, val in res.items():
        print(f"{key}: {val}")


def get_dims(csl: str):
    strlst = csl.split(',')
    return list(map(lambda s: int(s), strlst))


docstr = f'''Exam Calculator
usage:
    {argv[0]} conv-reuse <tile-dims> <mask-dims>
    {argv[0]} warp-divergence <block-x> <block-y> <block-z>
                              <img-x> <img-y> <img-z> <warp-sz>
    {argv[0]} (-h | --help)

Commands:
    conv-reuse      Calculate the average reuse of an internal tile
    warp-divergence Produce a list of divergent warps

Options:
    -h --help       Show this screen

Arguments:
    tile-dims       comma-seperated list of dimension sizes (i.e., "16,16,8")
    mask-dims       comma-seperated list of dimension sizes (i.e., "16,16,8")
'''

if __name__ == '__main__':
    args = docopt(docstr)

    if args['conv-reuse']:
        tile = get_dims(args['<tile-dims>'])
        mask = get_dims(args['<mask-dims>'])
        if len(tile) != len(mask):
            print("<mask-dims> and <tile-dims> must be same dimension",
                  file=stderr)
            exit(1)
        if len(tile) == 0:
            print("<tile-dim> must be non-zero dimension", file=stderr)
            exit(1)
        res = conv_reuse(tile, mask)
    elif args['warp-divergence']:
        if args['<img-z>'] is None:
            res = warp_divergence2d(int(args['<block-x>']),
                                    int(args['<block-y>']),
                                    int(args['<img-x>']),
                                    int(args['<img-y>']),
                                    int(args['<warp-sz>']))
        else:
            res = warp_divergence3d((int(args['<block-x>']),
                                    int(args['<block-y>']),
                                    int(args['<block-z>'])),
                                    (int(args['<img-x>']),
                                    int(args['<img-y>']),
                                    int(args['<img-z>'])),
                                    int(args['<warp-sz>']))

    print_results(res)
