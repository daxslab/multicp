#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import multiprocessing
import sys
import time
import threading
import os

# from osutils.fileutils import *


class CTError(Exception):
    def __init__(self, errors):
        self.errors = errors


class Progress:

    def __init__(self):
        self.total = 0.1
        self.progress = 0

    def set_progress(self, progress):
        self.progress = progress
        # self.show()

    def set_total(self, total):
        self.total = total

    def get_progress(self):
        return self.progress

    def get_total(self):
        return self.total

    def get_percent(self):
        # percent = self.progress*1.0/self.total if self.progress*1.0/self.total <= 1 else 1
        return self.progress*1.0/self.total

    def show(self):

        sys.stdout.write("\033[F")
        # text = u"\r{} de {} {}%".format(self.progress, self.total, int(self.get_percent()*100))
        print "{} de {} {}%".format(self.progress, self.total, int(self.get_percent()*100))

        # print "%s de %s %s %" % (self.progress, self.total, self.get_percent())
        # print str(self.progress)+" de "+str(self.total)+" "+self.get_percent()+"%"
        # sys.stdout.write("\033[K")
        # print str(self.progress)+" de "+str(self.total)

        # sys.stdout.flush()
        # sys.stdout.write(text)
        sys.stdout.flush()


def get_block_size(file):
    """
    try to find optimal block size for copy
    :param file: file in FS
    :return: bites block size
    """
    if get_os_type() == 'unix':
        statvfs = os.statvfs(file)
        return int(statvfs.f_frsize)
    elif get_os_type() == 'windows':
        return 4*1024


def copy_file(src, dst=[], progress=None, only_new_file=True, buffer_size=128*1024):
    out_files = dict.fromkeys(dst)
    if only_new_file:
        # copy only newer files
        out_files = []
        src_modified = time.ctime(os.path.getmtime(src))
        for dest in dst:
            if os.path.exists(dest):
                dest_modified = time.ctime(os.path.getmtime(dest))
                if src_modified > dest_modified:
                    out_files.append(dest)
                elif (src_modified == dest_modified) and (os.path.getsize(src) != os.path.getsize(dest)):
                    out_files.append(dest)
            else:
                out_files.append(dest)
        out_files = dict.fromkeys(out_files)
    try:
        # size = os.path.getsize(src)
        fin = open(src)
        for dst_file in out_files:
                out_files[dst_file] = open(dst_file, 'wb')

        while 1:
            copy_buffer = fin.read(buffer_size)
            if not copy_buffer:
                break
            workers = []
            for dst_file in out_files:
                workers.append(threading.Thread(target=copy_worker, args=(copy_buffer, out_files[dst_file],)))
                # workers.append(multiprocessing.Process(target=copy_worker, args=(copy_buffer, out_files[dst_file],)))
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join()
            # progress.set_progress(progress.progress + BUFFER_SIZE)
            # progress.set_progress(progress.progress + sys.getsizeof(x))
        # progress.set_progress(progress.progress + size)

    finally:
        try:
            os.close(fin)
        except:
            pass
        try:
            for key in out_files:
                os.close(out_files[key])
        except:
            pass


def copy_worker(stream, fout):
    fout.write(stream)
    return


def copytree(src, dst=[], symlinks=False, ignore=[], progress=None, only_new_file=True, buffer_size=16*1024*1024, verbose=False):
    # names = os.listdir(src)
    for dest_file in dst:
        if not os.path.exists(dest_file):
            os.makedirs(dest_file)
    errors = []
    if os.path.isdir(src):
        names = os.listdir(src)
        for name in names:
            if name in ignore:
                continue
            srcname = os.path.join(src, name)
            dstname = [os.path.join(a, name) for a in dst]
            try:
                if symlinks and os.path.islink(srcname):
                    linkto = os.readlink(srcname)
                    for dst_file in dstname:
                        os.symlink(linkto, dst_file)
                elif os.path.isdir(srcname):
                    copytree(srcname, dstname, symlinks, ignore, progress, only_new_file=only_new_file, buffer_size=buffer_size)
                else:
                    copy_file(srcname, dstname, progress, only_new_file=only_new_file, buffer_size=buffer_size)
                    if verbose:
                        print "copied "+srcname+ " to "+str(dstname)
            except (IOError, os.error), why:
                errors.append((srcname, dstname, str(why)))
            except CTError, err:
                errors.extend(err.errors)
    else:
        try:
            srcname = os.path.basename(src)
            dstname = [os.path.join(a, srcname) for a in dst]
            copy_file(src, dstname, progress, only_new_file=only_new_file, buffer_size=buffer_size)
            if verbose:
                print "copied "+src+ " to "+dstname
        except (IOError, os.error), why:
            errors.append((src, dstname, str(why)))
        except CTError, err:
            errors.extend(err.errors)
    if errors:
        raise CTError(errors)


def get_human_readable(size, precision=2):
    """
        Get human readable file size
    """
    suffixes=['B','KiB','MiB','GiB','TiB']
    suffixIndex = 0
    while size >= 1024:
        suffixIndex += 1
        size = size/1024.0
    return "%.*f %s"%(precision,size,suffixes[suffixIndex])


def main():

    prog = 'multicp'
    version = '%(prog)s 0.1.1'
    description = 'Multiple destination copy'
    epilog = version+' - (C) 2015 Carlos Cesar Caballero Díaz, Daxlab.'

    import argparse

    parser = argparse.ArgumentParser(prog=prog,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=description,
                                     epilog=epilog)

    parser.add_argument('--version', action='version', version=version,
                        help='show program\'s version number and exit')
    parser.add_argument('-b', '--buffer-size', action='store', type=int, default=16*1024*1024, dest='buffer_size',
                        metavar="Buffer Size",
                        help='define copy buffer size')
    parser.add_argument('-n', '--only-newer-files', action='store_true', dest='only_new_file',
                        help='only copy files with newer modification dates if exists in destination')
    parser.add_argument('-v', '--verbose', action='store_true', dest='verbose',
                        help='run in verbose mode, display copy information')
    parser.add_argument("source", metavar="Source file")
    parser.add_argument("dest", nargs='+', metavar="Destination files")

    args = parser.parse_args()


    copytree(args.source, args.dest, buffer_size=args.buffer_size, only_new_file=args.only_new_file, verbose=args.verbose)


if __name__ == '__main__':
    main()