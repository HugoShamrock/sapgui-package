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
import subprocess
import sys
import tempfile
from email.Utils import formatdate
from optparse import OptionParser

verbose = False

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
        dir = glob.glob(os.path.join(destdir,'usr/lib/sapgui/SAPGUI*rev*'))[0]
        version = os.path.basename(dir)[6:]
    except IndexError:
        raise SapGuiPkgError, "Cannot determin version number from subdir '%s'" % dir
    if not re.match("[0-9\.]+rev[0-9]+", version):
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
Architecture: i386
Depends: ${shlibs:Depends}, java2-runtime
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


def gen_rules(debiandir):
    contents = """#!/usr/bin/make -f
export DH_COMPAT=5

DEB_DH_STRIP_ARGS=nostrip
DEB_DH_SHLIBDEPS_ARGS_ALL=-- --warnings=1
include /usr/share/cdbs/1/rules/debhelper.mk

install/sapgui::
	rm -rf dest/usr/lib/sapgui/SAPGUI
"""
    write_file(debiandir, "rules", contents)
    os.chmod(os.path.join(debiandir,"rules"), 0755)


def gen_links(debiandir, version):
    contents = """usr/lib/sapgui/SAPGUI%(version)s/doc usr/share/doc/sapgui/doc
usr/lib/sapgui/SAPGUI%(version)s/bin/guilogon usr/bin/sapguilogon
usr/lib/sapgui/SAPGUI%(version)s/bin/guistart usr/bin/sapguistart
""" % dict(version=version)
    write_file(debiandir, "links", contents)


def build_sapgui_deb(tmpdir):
    curdir = os.path.abspath(os.path.curdir)
    os.chdir(tmpdir)
    subprocess.call(["fakeroot", "dpkg-buildpackage", "-b" ,"-uc", "-us"])
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
    (options, args) = parser.parse_args(argv[1:])

    verbose = options.verbose

    try:
        if len(args) != 1:
            raise SapGuiPkgError, "No jar given try '%s--help'" % prog
        else:
            jar = args[0]

        tmpdir = tempfile.mkdtemp(prefix=prog)
        destdir = os.path.join(tmpdir, 'dest')
        print "Extracting '%s' to '%s'" % (jar, destdir)
        extract_sapgui_jar(jar, destdir)
        debiandir = os.path.join(tmpdir, 'debian')
        os.mkdir(debiandir)
        sg_version = get_version(destdir)
        gen_changelog(debiandir, version, options.maintainer, options.email, sg_version)
        gen_control(debiandir, version, options.maintainer, options.email)
        gen_rules(debiandir)
        gen_install(debiandir)
        gen_copyright(debiandir)
        gen_links(debiandir, sg_version)
        print "Building Debain package at '%s'" % tmpdir
        build_sapgui_deb(tmpdir)
    except SapGuiPkgError, msg:
        print >>sys.stderr, msg
    else:
        result = os.path.abspath(os.path.join(tmpdir,"..","sapgui_%s_i386.deb" % sg_version))
        print "Created sapgui package at %s" % result
        ret = 0

    if tmpdir:
        if verbose:
            print "Cleaning up Tempdir at %s" % tmpdir
        subprocess.call(["/bin/rm", "-rf", "%s" % tmpdir])

    return ret

if __name__ == "__main__":
    sys.exit(main(sys.argv))

# vim:et:ts=4:sw=4:et:sts=4:ai:set list listchars=tab\:»·,trail\:·:
