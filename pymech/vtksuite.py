"""Module for converting exadata objects to vtk"""
import numpy as np
from tvtk.api import tvtk, write_data


__all__ = ("exa2vtk", "writevtk")


# ==============================================================================
def exa2vtk(field, downsample=False):
    """A function for converting exadata to vtk data

    Parameters
    ----------
    field : exadata
            a dataset in nekdata format
    downsample : bool
            flag T/F
    """
    #
    if downsample:
        ixs = field.lr1[0] - 1
        iys = field.lr1[1] - 1
        izs = max(field.lr1[2] - 1, 1)
    else:
        ixs = 1
        iys = 1
        izs = 1
    #
    iix = range(0, field.lr1[0], ixs)
    nix = len(iix)
    iiy = range(0, field.lr1[1], iys)
    niy = len(iiy)
    iiz = range(0, field.lr1[2], izs)
    niz = len(iiz)
    #
    nppel = nix * niy * niz
    nepel = (nix - 1) * (niy - 1) * max((niz - 1), 1)
    nel = field.nel * nepel
    #
    if field.ndim == 3:
        nvert = 8
        cellType = tvtk.Hexahedron().cell_type
    else:
        nvert = 4
        cellType = tvtk.Quad().cell_type
    #
    ct = np.array(nel * [cellType])
    of = np.arange(0, nvert * nel, nvert)

    ce = np.zeros(nel * (nvert + 1))
    ce[np.arange(nel) * (nvert + 1)] = nvert

    if field.var[0] != 0:
        r = np.zeros((nvert * nel, 3))
    if field.var[1] != 0:
        v = np.zeros((nvert * nel, 3))
    if field.var[2] == 1:
        p = np.zeros(nvert * nel)
    if field.var[3] == 1:
        T = np.zeros(nvert * nel)
    if field.var[4] != 0:
        S = np.zeros((nvert * nel, field.var[4]))
    #
    ice = -(nvert + 1)


    for iel in range(field.nel):
        for iz, ez in enumerate(iiz):
            for iy, ey in enumerate(iiy):
                for ix, ex in enumerate(iix):
                    iarray = iel * nppel + ix + iy * nix + iz * (nix * niy)

                    # Downsample copy into a column vector
                    if field.var[0] == 3:
                        r[iarray, :] = field.elem[iel].pos[:, ez, ey, ex]
                    if field.var[1] == 3:
                        v[iarray, :] = field.elem[iel].vel[:, ez, ey, ex]
                    if field.var[2] == 1:
                        p[iarray] = field.elem[iel].pres[:, ez, ey, ex]
                    if field.var[3] == 1:
                        T[iarray] = field.elem[iel].temp[:, ez, ey, ex]
                    if field.var[4] != 0:
                        S[iarray, :] = field.elem[iel].scal[:, ez, ey, ex]
        if field.var[0] == 3:
            for iz in range(max(niz - 1, 1)):
                for iy in range(niy - 1):
                    for ix in range(nix - 1):
                        ice = ice + nvert + 1
                        for face in range(field.ndim - 1):
                            ce[ice + face * 4 + 1] = (
                                iel * nppel + ix + iy * nix + (iz + face) * nix * niy
                            )
                            ce[ice + face * 4 + 2] = (
                                iel * nppel
                                + ix
                                + 1
                                + iy * nix
                                + (iz + face) * nix * niy
                            )
                            ce[ice + face * 4 + 3] = (
                                iel * nppel
                                + ix
                                + 1
                                + (iy + 1) * nix
                                + (iz + face) * nix * niy
                            )
                            ce[ice + face * 4 + 4] = (
                                iel * nppel
                                + ix
                                + (iy + 1) * nix
                                + (iz + face) * nix * niy
                            )

    # create the array of cells
    ca = tvtk.CellArray()
    ca.set_cells(nel, ce)
    # create the unstructured dataset
    dataset = tvtk.UnstructuredGrid(points=r)
    # set the cell types
    dataset.set_cells(ct, of, ca)
    # set the data
    idata = 0
    if field.var[1] != 0:
        dataset.point_data.vectors = v
        dataset.point_data.vectors.name = "vel"
        idata += 1
    if field.var[2] == 1:
        dataset.point_data.scalars = p
        dataset.point_data.scalars.name = "pres"
        idata += 1
    if field.var[3] == 1:
        dataset.point_data.add_array(T)
        dataset.point_data.get_array(idata).name = "temp"
        idata += 1
    if field.var[4] != 0:
        for ii in range(field.var[4]):
            dataset.point_data.add_array(S[:, ii])
            dataset.point_data.get_array(ii + idata).name = "scal_%d" % (ii + 1)
    #
    dataset.point_data.update()
    #
    return dataset


def writevtk(fname, data):
    """A function for writing binary data in the XML VTK format

    Parameters
    ----------
    fname : str
            file name
    data : exadata
            data organised after reading a file

    """
    ext = ".vtp"
    if not fname.endswith(ext):
        fname += ext

    vtk_dataset = exa2vtk(data)
    write_data(vtk_dataset, fname)
