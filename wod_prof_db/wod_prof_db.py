#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Main module of wod_prof_db."""


import argparse
import numpy as np
import glob
import os
from wodpy import wod
import subprocess


def get_prof_data(profile):
    nlevs = profile.n_levels()
    year, mon, day = profile.year(), profile.month(), profile.day()
    p_datetime = profile.datetime()
    probe_type = probe_type_as_str(np.int(profile.probe_type()))
    lat, lon = profile.latitude(), profile.longitude()
    pmin = profile.p().min()
    pmax = profile.p().max()
    # p_pres_qc = profile.p_profile_qc()
    # p_z_qc = profile.z_profile_qc()
    p_temp_qc = profile.t_profile_qc()
    p_sal_qc = profile.s_profile_qc()
    prof_ok = assess_prof(profile)  # returns bool (False = something is wrong)
    pres = profile.p()
    sal = profile.s()
    temp = profile.t()
    uz = profile.z_unc()
    usal = profile.s_unc()
    utemp = profile.t_unc()
    z = profile.z()
    dp_m = np.diff(pres).mean()
    dz_m = np.diff(z).mean()
    prof_data_tuple = (probe_type, nlevs, year, mon, day, p_datetime, lat, lon,
                       pmin, pmax, dp_m, dz_m, p_sal_qc, p_temp_qc,
                       pres, sal, temp, z, usal, utemp, uz)
    return prof_data_tuple, prof_ok


def probe_type_as_str(probe_type):
    if probe_type == 4:
        return 'CTD'
    elif probe_type == 5:
        return 'STD'
    elif probe_type == 6:
        return 'XCTD'
    elif probe_type == 2:
        return 'XTD'
    elif probe_type == 9:
        return 'FLOAT'
    elif probe_type == 0:
        return 'UNKNOWN'
    else:
        return 'READ FAIL'


def assess_prof(profile, g_crit=.5, QS=3):
    '''Check for p, s, t, lat, lon, date integraty,
    then check if minimum qc score for p, s, t is satisfied'''
    p_test = len(profile.p().compressed()) / profile.n_levels() < g_crit
    s_test = len(profile.s().compressed()) / profile.n_levels() < g_crit
    t_test = len(profile.t().compressed()) / profile.n_levels() < g_crit
    if p_test or t_test or s_test:
        return False
    if profile.t_profile_qc() is None or profile.s_profile_qc() is None:
        return False
    if profile.t_profile_qc() < QS or profile.s_profile_qc() < QS:
        return True
    else:
        return False


def main():
    # print('This executes the wod_prof_db package\n')

    parser = argparse.ArgumentParser(description="setup WOD profile lookup database")
    parser.add_argument("source_dir",
                        type=str,
                        help="full path to directory containing source data (e.g. download folder)")
    parser.add_argument("dest_dir",
                        type=str,
                        nargs='?',
                        help="directory path where output array will reside")
    parser.add_argument("wild_card",
                        type=str,
                        nargs='?',
                        help="wild card string to narrow input files")
    args = parser.parse_args()

    cur_dir = subprocess.check_output("pwd", shell=True)[:-1]

    print("source dir is " + args.source_dir)
    source_dir = args.source_dir  # dir of source data (wod files)

    if args.dest_dir:
        print("dest dir is " + args.dest_dir)
        dest_dir = args.dest_dir
    else:
        print("creating profile_pool dir in current dir\n")
        dest_dir = cur_dir + "/profile_db/"  # where to put database

    if not os.path.isdir(dest_dir):
        os.system("mkdir " + dest_dir)
        print("creating destination directory")

    # use glob to form a list of input files:
    if args.wild_card:
        prof_files = glob.glob(source_dir + '/ocldb' + args.wild_card)
        print(prof_files)
    else:
        prof_files = glob.glob(source_dir + '/ocldb*')
        print(prof_files)
    # prof_files.sort(key=lambda x: [int(x.split('-')[2])])  # no need for sort

    # prepare look-up table array/list/dict
    # maybe list less ideal because it's slow and lists may require more memory to fill up
    dbase = []  # dbase is the list of profiles that contains profile info

    # loop over input files, retrieve the necessary info and store it in the
    # appropriate place in
    print("\nputting together database: list filling loop\n")
    for dafile in prof_files:
        print("\nWorking on file: " + dafile + "\n")
        fid = open(dafile)
        profile = wod.WodProfile(fid)
        prof_data, prof_ok = get_prof_data(profile)
        if prof_ok:
            dbase.append(prof_data)
        last_prof = profile.is_last_profile_in_file(fid)
        while not last_prof:
            profile = wod.WodProfile(fid)
            prof_data, prof_ok = get_prof_data(profile)
            if prof_ok:
                dbase.append(prof_data)
            last_prof = profile.is_last_profile_in_file(fid)
    dbase = np.array(dbase, dtype=[("probe_type", '|S21'), ('nlevs', 'int32'),
                                   ('year', 'int32'), ('month', 'int32'),
                                   ('day', 'int32'), ('date', 'O'),
                                   ('lat', 'float32'), ('lon', 'float32'),
                                   ('pmin', 'float32'), ('pmax', 'float32'),
                                   ('dpm', 'float32'), ('dzm', 'float32'),
                                   ("ps_qc", 'int32'), ("pt_qc", 'int32'),
                                   ('pres', 'O'),
                                   ('sal', 'O'), ('temp', 'O'), ('z', 'O'),
                                   ('usal', 'O'), ('utemp', 'O'), ('uz', 'O')
                                   ])
    np.savez_compressed(dest_dir + "cal_wod_profile_info_database", dbase=dbase)


if __name__ == '__main__':
    main()
