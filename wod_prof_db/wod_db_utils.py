#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Module with utilities to interact with wod profile database arrays."""


import numpy as np
import gsw
from scipy.interpolate import pchip


def lonlat_metrics(alat):
    """
    For given latitudes, return meters per degree lon, m per deg lat

    Reference: American Practical Navigator, Vol II, 1975 Edition, p 5
    """
    rlat = alat*np.pi/180
    hx = 111415.13 * np.cos(rlat) - 94.55 * np.cos(3 * rlat)
    hy = 111132.09 - 566.05 * np.cos(2 * rlat) + 1.2 * np.cos(4 * rlat)
    return hx, hy


def diffxy_from_difflonlat(dlon, dlat, alat):
    """
    Convert increments dlon, dlat in degrees to meters, for latitude alat.

    alat can be a scalar or an array with the dimensions of dlon and dlat.

    """
    hx, hy = lonlat_metrics(alat)
    dx = dlon * hx
    dy = dlat * hy
    return dx, dy


def lonlat_inside_km_radius(lons, lats, pos, kmrad):
    """
    Return a boolean array with True where the positions
    specified by *lons*, *lats* are less than *kmrad* kilometers
    from the point *pos* (a lon, lat pair).
    """
    dlon = np.asanyarray(lons) - pos[0]
    dlat = np.asanyarray(lats) - pos[1]
    dx, dy = diffxy_from_difflonlat(dlon, dlat, pos[1])
    kmdist = np.sqrt(dx**2 + dy**2) / 1000.0
    return kmdist < kmrad


def quik_quality_control(dbase, dp_crit=10.):
    """
    Quality control using WOD flags (only takes acceptable casts) and
    the dp criteria: no cast with low resolution allowed.
    """
    good_idxs = np.logical_and(dbase['pt_qc'] == 0,
                               dbase['ps_qc'] == 0)
    good_idxs = np.logical_and(good_idxs, dbase['dpm'] <= dp_crit)
    return dbase[good_idxs]


def regrid_2_std_z(var_arr, p_arr, std_z):
    """
    Need smoothing before interp, need done inside z_interp; try MAUD
    """
    reg_arr = np.asarray([z_pinterp(var, pres, std_z
                                    ) for var, pres in zip(var_arr, p_arr)])
    return reg_arr


def z_pinterp(var, pres, std_z):
    """ deals with masked ones
    """
    if np.count_nonzero(~var.mask) < 2:
        bad = np.empty((len(std_z),))
        bad.fill(np.nan)
        return bad
    else:
        if any(pres[1:] < pres[:-1]):
            sidx = np.argsort(pres)
            pres, var = pres[sidx], var[sidx]
        fp = pchip(pres[~var.mask], var.compressed(), extrapolate=False)
        return fp(std_z)


# def wrap_regrid_2_std_z(vars_arr, p_arr, std_z):
#     reg_arr = np.vstack([regrid_2_std_z(var_arr, p_arr,
#                                         std_z) for var_arr in vars_arr.T])
#     reg_arr = np.moveaxis(reg_arr.reshape((vars_arr.shape[1],
#                                            vars_arr.shape[0],
#                                            len(std_z))), 0, -1)
#     return reg_arr
#
#
# def derive_variables(dbase, which_ones='all'):
#     """
#     Also include density, potential temp and density; and uncertainties!!
#     """
#     SA_dat = np.asarray([gsw.SA_from_SP(dbase['sal'][n], dbase['pres'][n],
#                                         dbase['lon'][n],
#                                         dbase['lat'][n]
#                                         ) for n in range(0, len(dbase))])
#     CT_dat = np.asarray([gsw.CT_from_t(SA_dat[n], dbase['temp'][n],
#                                        dbase['pres'][n]
#                                        ) for n in range(0, len(dbase))])
#     N2_dat = np.asarray([gsw.Nsquared(SA_dat[n], CT_dat[n], dbase['pres'][n],
#                                       dbase['lat'][n], alphabeta=True,
#                                       ) for n in range(0, len(dbase))])
#     if which_ones == 'all':
#         return tuple(SA_dat, CT_dat, N2_dat, Sig_dat, Rho_dat, Theta_dat)
#     elif which_ones == 'N2':
#         return N2_dat


def derive_variables(dbase, which_ones='all'):
    """
    Also include density, potential temp and density; and uncertainties!!
    """
    SA_dat = [gsw.SA_from_SP(dbase['sal'][n], dbase['pres'][n],
                             dbase['lon'][n], dbase['lat'][n]
                             ) for n in range(0, len(dbase))]
    CT_dat = [gsw.CT_from_t(SA_dat[n], dbase['temp'][n],
                            dbase['pres'][n]
                            ) for n in range(0, len(dbase))]
    N2_dat = [gsw.Nsquared(SA_dat[n], CT_dat[n], dbase['pres'][n],
                           dbase['lat'][n], alphabeta=True,
                           ) for n in range(0, len(dbase))]
    if which_ones == 'all':
        return tuple(SA_dat, CT_dat, N2_dat, Sig_dat, Rho_dat, Theta_dat)
    elif which_ones == 'N2':
        return N2_dat


def wrap_regrid_2_std_z(vars_arr, p_arr, std_z, which_ones):
    if which_ones == 'N2':
        reg_arr = np.vstack([z_pinterp(vr, var_arr[1], std_z
                                       ) for var_arr in vars_arr for vr in var_arr[:1] + var_arr[2:]])
        # if reg_arr.ndim > 2:
        reg_arr = np.moveaxis(np.reshape(reg_arr,
                                         (len(vars_arr),
                                          len(vars_arr[0][:1] + vars_arr[0][2:]),
                                          len(std_z))), 1, -1)
        # elif reg_arr.ndim == 2:
        #     reg_arr = np.transpose(reg_arr)[np.newaxis]
    return reg_arr


def search_assemble_radavg(wod_dbase, lon_arr, lat_arr, std_z=None,
                           which_ones='N2', kmrad=1e2):
    if std_z is None:
        zmax = 6000.e0
        dz = 5.e0
        std_z = np.arange(0, zmax + dz, dz)

    # avg_vars_grd = np.ma.empty(lon_arr.shape, dtype='O')
    avg_vars_grd = []
    std_vars_grd = []
    min_vars_grd = []
    max_vars_grd = []
    for n, (lonc, latc) in enumerate(zip(lon_arr, lat_arr)):
        print(n, lonc, latc)
        locs = lonlat_inside_km_radius(wod_dbase['lon'], wod_dbase['lat'],
                                       (lonc, latc), kmrad)
        wod_loc_subset = wod_dbase[locs]
        wod_loc_subset = quik_quality_control(wod_loc_subset)
        print("found %s good profiles in area" %len(wod_loc_subset))
        if len(wod_loc_subset) > 0:
            vars_arr = derive_variables(wod_loc_subset, which_ones=which_ones)
            # if which_ones == 'N2':
            #     vars_grd = wrap_regrid_2_std_z(vars_arr[:, [0, 2, 3]],
            #                                    vars_arr[:, 1], std_z)
            #     avg_vars_grd[n] = np.mean(vars_grd, axis=0)
            vars_grd = wrap_regrid_2_std_z(vars_arr, wod_loc_subset['pres'],
                                           std_z, which_ones)
            # avg_vars_grd[n] = np.nanmean(vars_grd, axis=0)
            avg_vars_grd.append(np.nanmedian(vars_grd, axis=0))
            std_vars_grd.append(np.nanstd(vars_grd, axis=0))
            min_vars_grd.append(np.nanquantile(vars_grd, .05, axis=0))
            max_vars_grd.append(np.nanquantile(vars_grd, .95, axis=0))
        # else:
            # bad = np.empty((len(std_z), 3))  # this is nor N2, need general
            # bad.fill(np.nan)
            # avg_vars_grd[n] = bad
            # avg_vars_grd[n] = np.nan  # use this to later eliminate the entry

    return np.asarray(avg_vars_grd), np.asarray(std_vars_grd), np.asarray(min_vars_grd), np.asarray(max_vars_grd)
    # return np.reshape(np.concatenate(avg_vars_grd),
    #                   (len(avg_vars_grd), len(std_z), vars_grd.shape[-1]))


def main():
    wod_dbase = np.load('../data/cal_wod_profile_info_database.npz',
                        allow_pickle=True)['dbase']

    ship_file = ('/home/smullersoares/projects/science/adcp_for_swot/',
                 'adcp_swot/data/clean_stacks_NEandSE_z45and125.npz')
    ship_data = np.load(ship_file, allow_pickle=True)

    # ship_lats = np.hstack(ship_data['data_stack_NE_z45']['lats'])
    # ship_lons = np.hstack(ship_data['data_stack_NE_z45']['lons'])

    is_in_da_years = np.logical_and(ship_data['year'] >= 1994,
                                    ship_data['year'] <= 2018)
    is_in_da_mon = ship_data['month'] == 1
    is_what_I_want = np.logical_and(is_in_da_years, is_in_da_mon)
    # wod_mon_subset = wod_dbase['month'] == 1
    # first_subset = ship_data['data_stack_NE_z45'][is_what_I_want]
    kmrad = 250e0
    # which_ones = 'N2'

    mon_avg_N2_grd = np.empty((12,), dtype='O')
    for m in range(1, 13):
        is_in_da_mon = ship_data['month'] == m
        is_what_I_want = np.logical_and(is_in_da_years, is_in_da_mon)
        ship_subset = ship_data[is_what_I_want]

        wod_mon_subset = wod_dbase['month'] == m
        avg_N2_grd = search_assemble_radavg(wod_dbase[wod_mon_subset],
                                            ship_subset['lon_center'],
                                            ship_subset['lat_center'],
                                            kmrad=kmrad)
        mon_avg_N2_grd[m - 1] = avg_N2_grd


if __name__ == '__main__':
    main()
