from __future__ import print_function

# a b c alpha beta gamma
# Na Nb Nc
# (((z) y) x)

import numpy as np
import math
import linecache
import argparse
import scipy.interpolate as interp


class AkwGrd(object):

    def __init__(self, filein, shift_origin=False):

        print("\nReading '{}'...".format(filein))
        with open(filein, 'r') as fin:
            l = fin.readline()
            self.N_kx, self.N_ky, self.N_kz, self.N_omega = map(int, l.replace('#', '').split())
            self.N_k = self.N_kx * self.N_ky * self.N_kz

            print("N_kx= ", self.N_kx)
            print("N_ky= ", self.N_ky)
            print("N_kz= ", self.N_kz)
            print("N_omega= ", self.N_omega)

            self.bvec = []
            for i in range(3):
                self.bvec.append(np.array(map(float, fin.readline().replace('#', '').split())))
                print("bvec{}: {}".format(i, self.bvec[-1]))

        # read mesh data
        self.data = np.loadtxt(args.path_input_file).reshape((self.N_kx, self.N_ky, self.N_kz, self.N_omega, 5))

        if shift_origin:
            def shift(nx):
                # Return the list [N/2, N/2+1, ..., N-1, 0, 1, ..., N/2-1]
                return np.roll(range(nx), nx // 2)
            self.data = self.data[shift(self.N_kx), :, :, :, :][:, shift(self.N_ky), :, :, :][:, :, shift(self.N_kz), :, :]

    def _interpolate_omega(self, omega):
        """
        Compute A(k, w) for a given value of w=omega by interpolation

        Parameters
        ----------
        omega: float

        Returns
        -------
        ak: numpy.ndarray[N_kx, N_ky, N_kz]

        """

        omega_mesh = self.data[0, 0, 0, :, 3]
        omega_min = omega_mesh[0]
        omega_max = omega_mesh[-1]
        print("omega_min={}, omega_max={}".format(omega_min, omega_max))
        if omega < omega_min or omega_max < omega:
            raise RuntimeError("omega={} is out of interpolation range!".format(omega))

        akw = self.data[:, :, :, :, 4].reshape((self.N_k, self.N_omega))
        ak = np.empty(self.N_k, dtype=float)

        # interpolate
        print("\nInterpolating...")
        for k in range(self.N_k):
            f = interp.interp1d(omega_mesh, akw[k, :], kind='cubic')
            ak[k] = f(omega)
        print("done")

        return ak.reshape((self.N_kx, self.N_ky, self.N_kz))

    def _lattice_info(self):
        """
        Find a, b, c, alpha, beta, gamma from bvec

        Returns
        -------
        avec: numpy.ndarray[3]
        angle: numpy.ndarray[3]
        """

        # Get norm of each vector -> a b c
        avec = np.zeros(3)
        angle = np.zeros(3)  # order: alpha beta gamma
        for i in range(3):
            avec[i] = np.linalg.norm(self.bvec[i])

        # Get angle between each vector -> alpha beta gamma
        for i in range(3):
            temp = math.acos(np.dot(self.bvec[(i+1) % 3], self.bvec[(i+2) % 3])/(avec[(i+1) % 3]*avec[(i+2) % 3]))
            angle[i] = math.degrees(temp)

        return avec, angle

    def write_grd(self, fileout, omega):

        # A[kx, ky, kz]
        ak = self._interpolate_omega(omega)

        # lattice information
        avec, angles = self._lattice_info()

        # save in a file with GRD format
        print("\nSaving data into '{}' in GRD format...".format(fileout))
        with open(fileout, 'w') as fout:
            # self._write_header(fout)

            # header
            print("#", file=fout)
            for a in avec:
                print(a, end=" ", file=fout)
            for angle in angles:
                print(angle, end=" ", file=fout)
            print("", file=fout)
            print(self.N_kx, self.N_ky, self.N_kz, file=fout)

            for val in ak.reshape(-1):
                print(val, file=fout)
        print("done")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path_input_file',
                        action='store',
                        default=None,
                        type=str,
                        help="input file name.")
    parser.add_argument('path_output_file',
                        action='store',
                        default=None,
                        type=str,
                        help="output file name.")
    parser.add_argument('--omega',
                        required=True,
                        type=float,
                        help='Real frequency')
    parser.add_argument('--format', '-f',
                        type=str,
                        default='grd',
                        choices=['grd',],
                        help="data format")
    # parser.add_argument('--kz', type=int, default=None, help='wave vector along the z-direction')
    args = parser.parse_args()

    print("omega = {}".format(args.omega))
    print("format = {}".format(args.format))

    akw = AkwGrd(args.path_input_file)

    if args.format == 'grd':
        # save 3D data in GRD format
        akw.write_grd(args.path_output_file, args.omega)
