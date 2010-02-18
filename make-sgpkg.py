#!/usr/bin/python -u
# vim: set fileencoding=utf-8 :
#
# (C) 2009 Guido Guenther <agx@sigxcpu.org>
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
"""build a sapgui debian package"""

import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
from email.Utils import formatdate
from optparse import OptionParser

verbose = False
properties = "~/.platin.properties"

class SapGuiPkgError(Exception):
    pass


def extract_sapgui_jar(jar, destdir):
    cmd = [ "java", "-jar", "%s" % jar, "install", "-disableui",
             "-noshortcuts", "-silent", "-automatic", "-installdir",
             "%s/usr/lib/sapgui" % destdir ]
    if verbose:
        print " ".join(cmd)
    ret = subprocess.call(cmd)
    if ret:
        raise SapGuiPkgError, "Error extracting jar"


def write_file(debdir, name, contents):
    f = file(os.path.join(debdir, name), 'w')
    f.write(contents)
    f.close()


def get_version(destdir):
    dir = None
    try:
        dir = glob.glob(os.path.join(destdir, 'usr/lib/sapgui/SAPGUI*.*'))[0]
        version = os.path.basename(dir)[6:]
    except IndexError:
        raise SapGuiPkgError, "Cannot determin version number from subdir '%s'" % dir
    if not re.match("[0-9\.](rev[0-9]+)?", version):
        raise SapGuiPkgError, "Cannot determin version number from '%s'" % version
    return version


def gen_changelog(debiandir, version, name, email, sg_version):
    date = formatdate(localtime=True)
    contents="""sapgui (%(sg_version)s) unstable; urgency=low

  * This package was created with sap-gui-package %(version)s.

 -- %(name)s <%(email)s>  %(date)s
""" % dict(version=version, name=name, email=email, date=date,
           sg_version=sg_version)
    write_file(debiandir, "changelog", contents)


def gen_control(debiandir, version, name, email):
    contents = """Source: sapgui
Section: non-free/devel
Priority: optional
Maintainer: %(name)s <%(email)s>
Build-Depends: debhelper (>= 4.0.0)
Standards-Version: 3.8.0

Package: sapgui
Architecture: i386 amd64
Depends: ${shlibs:Depends}, openjdk-6-jre | sun-java6-bin | java6-runtime
Description: SAP GUI for the Java Environment
 This package has been automatically created with sapgui-package %(version)s
""" % dict(name=name, email=email, version=version)
    write_file(debiandir, "control", contents)


def gen_copyright(debiandir):
    contents = """For copyright information please look at
/usr/share/doc/sapgui/doc/license/
"""
    write_file(debiandir, "copyright", contents)


def gen_install(debiandir):
    contents = "dest/usr/* usr/"
    write_file(debiandir, "install", contents)


def gen_rules(debiandir, arch):
    if arch == "amd64":
        # ignore 32bit libs on amd64
        excludes = [ "libGnomeConnect.so", "libJPlatin.so" ]
        # exclude 32bit binaries
        excludes += [ "bin/sapftp", "bin/saphttp" ]
        # these were additionally shipped with 719:
        excludes += [ "libKde3Connect.so" ]
    else:
        # ignore 64bit libs on i386
        excludes = [ "libGnomeConnect64.so", "libJPlatin64.so" ]

    ignore_libs = " ".join([ "--exclude=%s" % e for e in  excludes ])

    contents = """#!/usr/bin/make -f
export DH_COMPAT=5

DEB_DH_STRIP_ARGS=nostrip
DEB_DH_SHLIBDEPS_ARGS_ALL=%s -- --warnings=1
include /usr/share/cdbs/1/rules/debhelper.mk

install/sapgui::
	rm -rf dest/usr/lib/sapgui/SAPGUI
""" % ignore_libs
    write_file(debiandir, "rules", contents)
    os.chmod(os.path.join(debiandir,"rules"), 0755)


def gen_links(debiandir, version):
    contents = """usr/lib/sapgui/SAPGUI%(version)s/doc usr/share/doc/sapgui/doc
usr/lib/sapgui/SAPGUI%(version)s/bin/guilogon usr/bin/sapguilogon
usr/lib/sapgui/SAPGUI%(version)s/bin/guistart usr/bin/sapguistart
usr/lib/sapgui/SAPGUI%(version)s/inst/hicolor/128x128/apps/guilogon.png   /usr/share/icons/hicolor/128x128/apps/guilogon.png
usr/lib/sapgui/SAPGUI%(version)s/inst/hicolor/128x128/apps/SAPClients.png /usr/share/icons/hicolor/128x128/apps/SAPClients.png
usr/lib/sapgui/SAPGUI%(version)s/inst/hicolor/64x64/apps/guilogon.png   /usr/share/icons/hicolor/64x64/apps/guilogon.png
usr/lib/sapgui/SAPGUI%(version)s/inst/hicolor/64x64/apps/SAPClients.png /usr/share/icons/hicolor/64x64/apps/SAPClients.png
usr/lib/sapgui/SAPGUI%(version)s/inst/hicolor/48x48/apps/guilogon.png   /usr/share/icons/hicolor/48x48/apps/guilogon.png
usr/lib/sapgui/SAPGUI%(version)s/inst/hicolor/48x48/apps/SAPClients.png /usr/share/icons/hicolor/48x48/apps/SAPClients.png
usr/lib/sapgui/SAPGUI%(version)s/inst/hicolor/32x32/apps/guilogon.png   /usr/share/icons/hicolor/32x32/apps/guilogon.png
usr/lib/sapgui/SAPGUI%(version)s/inst/hicolor/32x32/apps/SAPClients.png /usr/share/icons/hicolor/32x32/apps/SAPClients.png
usr/lib/sapgui/SAPGUI%(version)s/inst/hicolor/22x22/apps/guilogon.png   /usr/share/icons/hicolor/22x22/apps/guilogon.png
usr/lib/sapgui/SAPGUI%(version)s/inst/hicolor/22x22/apps/SAPClients.png /usr/share/icons/hicolor/22x22/apps/SAPClients.png
usr/lib/sapgui/SAPGUI%(version)s/inst/hicolor/16x16/apps/guilogon.png   /usr/share/icons/hicolor/16x16/apps/guilogon.png
usr/lib/sapgui/SAPGUI%(version)s/inst/hicolor/16x16/apps/SAPClients.png /usr/share/icons/hicolor/16x16/apps/SAPClients.png
""" % dict(version=version)
    write_file(debiandir, "links", contents)


def build_sapgui_deb(tmpdir):
    curdir = os.path.abspath(os.path.curdir)
    build_cmd = ["fakeroot", "dpkg-buildpackage", "-b" ,"-uc", "-us"]
    os.chdir(tmpdir)
    try:
        ret = subprocess.call(build_cmd)
    except OSError, msg:
        raise SapGuiPkgError, "Cannot run '%s': %s" % (" ".join(build_cmd), msg)
    if ret:
        raise SapGuiPkgError, "Error building package."
    os.chdir(curdir)


def main(argv):
    tmpdir = None
    ret = 1
    version = "@VERSION@"
    global verbose

    prog = os.path.basename(argv[0])
    parser = OptionParser(prog=prog, usage='%prog [options] /path/to/sapgui.jar', version="%prog " + version)
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", default=False,
                      help="verbose command execution")
    parser.add_option("--maintainer", default="Guido Günther",
                      help="full name used in the maintainer field of the package")
    parser.add_option("--email", default="agx@sigxpcu.org",
                      help="email address used in the maintainer field of the package")
    parser.add_option("--no-clean", action="store_false", dest="clean", default=True,
                      help="don't cleanup after build")
    (options, args) = parser.parse_args(argv[1:])

    verbose = options.verbose

    if os.getuid() == 0:
        print >>sys.stderr, "Don't run %s as root." % argv[0]
        sys.exit(1)

    if os.path.exists(os.path.expanduser(properties)):
        print >>sys.stderr, "%s exists - this can cause problems. Please remove the file first." % properties
        sys.exit(1)

    try:
        if len(args) != 1:
            raise SapGuiPkgError, "No jar given try '%s --help'" % prog
        else:
            jar = args[0]

        tmpdir = tempfile.mkdtemp(prefix=prog)
        pkgdir = os.path.join(tmpdir, "sapgui-java")
        destdir = os.path.join(pkgdir, 'dest')
        debiandir = os.path.join(pkgdir, 'debian')
        os.mkdir(pkgdir)
        os.mkdir(debiandir)

        print "Extracting '%s' to '%s'" % (jar, destdir)
        extract_sapgui_jar(jar, destdir)

        arch = os.popen("dpkg-architecture -qDEB_BUILD_ARCH").readlines()[0].strip()

        sg_version = get_version(destdir)
        pkg = "sapgui_%s_%s.deb" % (sg_version, arch)
        gen_changelog(debiandir, version, options.maintainer, options.email, sg_version)
        gen_control(debiandir, version, options.maintainer, options.email)
        gen_rules(debiandir, arch)
        gen_install(debiandir)
        gen_copyright(debiandir)
        gen_links(debiandir, sg_version)

        print "Building Debain package at '%s'" % pkgdir
        build_sapgui_deb(pkgdir)
        result = os.path.abspath(os.path.join(tmpdir, pkg))
        shutil.move(result, os.path.curdir)
    except SapGuiPkgError, msg:
        print >>sys.stderr, msg
    else:
        print "Created '%s'" % pkg
        ret = 0

    if tmpdir and options.clean:
        if verbose:
            print "Cleaning up tempdir at %s" % tmpdir
        shutil.rmtree(tmpdir)
        try:
            os.stat(os.path.expanduser(properties))
            os.unlink(os.path.expanduser(properties))
        except OSError:
            pass # ignore missing file or unlink error

    return ret

if __name__ == "__main__":
    sys.exit(main(sys.argv))

# vim:et:ts=4:sw=4:et:sts=4:ai:set list listchars=tab\:»·,trail\:·:
