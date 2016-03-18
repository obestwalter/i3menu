# -*- coding: utf-8 -*-
import sys
import subprocess
from collections import OrderedDict
from zope.component import getGlobalSiteManager
from zope.component import getUtilitiesFor
from zope.schema.interfaces import RequiredMissing
from zope.interface import implementer

from i3menu import logger
from i3menu.utils import safe_join, which, getch
from i3menu.config import SUBMENU_SIGN
from i3menu.config import MENUENTRY_SIGN
from i3menu.__about__ import __title__
from i3menu.interfaces import IMenuProvider
from i3menu.interfaces import IContextManager
from i3menu.interfaces import II3Connector
from i3menu.exceptions import NoInputError, SelectionNotValidError
from builtins import input


gsm = getGlobalSiteManager()


@implementer(IMenuProvider)
class ShellMenuProvider(object):
    priority = 0
    bold_text = '\033[1m'
    blue_text = '\033[94m'
    green_text = '\033[92m'
    end_colors = '\033[0m'

    def __init__(self, cmd, priority=0):
        self.mp = cmd
        self.priority = priority

    def prepareprompt(self, prompt=None, addprefix=True):
        if addprefix:
            prefix = '{bold}{blue}({prefix}){endc} '.format(
                bold=self.bold_text, blue=self.blue_text,
                prefix=__title__, endc=self.end_colors
            )
        else:
            prefix = ''
        prompt = prefix + str(prompt)
        return '%s: ' % prompt

    def printprompt(self, prompt):
        sys.stdout.write(prompt)
        sys.stdout.write('\n')

    def getinput(self):
        if len(self.entries):
            escapes = ['\x03', '\x04', '\x1b']  # ctrl-c, ctrl-d, esc
            ch = getch()
            if ch in escapes:
                raise NoInputError()
            return ch
        else:
            try:
                return input()
            except KeyboardInterrupt:  # ctrl+c
                raise NoInputError()
            except EOFError:  # ctrl+d
                raise NoInputError()

    def display_menu(self, entries):
        labels = []
        idx2entry = OrderedDict()
        for i, e in enumerate(entries):
            # icon = e.cascade and SUBMENU_SIGN or MENUENTRY_SIGN
            icon = ''
            idx = i + 1
            label = u'{color}{idx}{endc}: {l}{icon}'.format(
                color=self.green_text,
                endc=self.end_colors,
                idx=idx,
                l=e.title,
                icon=icon)
            labels.append(label)
            idx2entry[str(idx)] = e
        encoded_labels = safe_join(labels, '\n')
        sys.stdout.write(encoded_labels)
        if len(entries):
            sys.stdout.write('\n')
            valid_input = '[{mini}-{maxi}]'.format(
                mini=idx2entry.keys()[0],
                maxi=idx2entry.keys()[-1])
            sys.stdout.write('{valid_input} '.format(valid_input=valid_input))
        res = self.getinput()
        if len(entries) == 0:
            return res
        entry = idx2entry.get(res)
        if not entry:
            raise SelectionNotValidError()
        return entry

    def __call__(self, entries=None, prompt=None):
        if entries:
            self.entries = entries
        prompt = self.prepareprompt(prompt)
        self.printprompt(prompt)
        return self.display_menu(entries)

rofimp = ShellMenuProvider('shell', priority=10)
gsm.registerUtility(rofimp, IMenuProvider, 'shell')


@implementer(IMenuProvider)
class MenuProvider(object):
    priority = 0

    def __init__(self, cmd, priority=0):
        self.mp = which(cmd)
        self.priority = priority

    def preparelabels(self, entries):
        labels = OrderedDict()
        for i, e in enumerate(entries):
            # icon = e.cascade and SUBMENU_SIGN or MENUENTRY_SIGN
            icon = ''
            label = u'{idx}: {l}{icon}'.format(
                idx=i,
                l=e.title and e.title or e.token,
                icon=icon)
            labels[label] = e
        return labels

    def prepareprompt(self, prompt=None, addprefix=True):
        if addprefix:
            prompt = u'({appname}) {prompt}'.format(
                appname=__title__,
                prompt=prompt)
        return '"%s": ' % prompt

    def preparecmd(self, prompt, labels):
        return self.mp

    def run(self, cmd, options):

        logger.info('Display menu: cmd={cmd} options={options}'.format(
            cmd=repr(cmd), options=repr(options.keys())))
        cmd = subprocess.Popen(cmd,
                               shell=True,
                               stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
        out, err = cmd.communicate('\n'.join(options).encode('utf-8'))
        if cmd.returncode:
            raise NoInputError()
        return out

    def sanitizeinput(self, res):
        if res is not None:
            res = res.decode('utf-8').strip('\n')
            # res = res.strip(SUBMENU_SIGN)
            # res = res.strip(MENUENTRY_SIGN)
            # res = res.split(': ', 1)[-1]
        return res

    def __call__(self, entries, prompt=None):
        prompt = self.prepareprompt(prompt)
        labels = len(entries) and self.preparelabels(entries) or {}
        cmd = self.preparecmd(prompt, entries)
        res = self.sanitizeinput(self.run(cmd, labels))
        if len(entries) == 0:
            return res
        entry = labels.get(res)
        if not entry:
            raise SelectionNotValidError()
        return entry


class DmenuMenuProvider(MenuProvider):
    def __init__(self, cmd='dmenu', priority=0):
        self.mp = which(cmd)
        self.priority = priority

    def preparecmd(self, prompt, entries=None):
        cmdargs = '-p {prompt} -l {lines}'.format(
            prompt=prompt, lines=len(entries))
        return '{cmd} {cmdargs}'.format(
            cmd=self.mp,
            cmdargs=cmdargs,
        )


class RofiMenuProvider(MenuProvider):
    def __init__(self, cmd='rofi', priority=0):
        self.mp = which(cmd)
        self.priority = priority

    def preparecmd(self, prompt, entries=None):
        cmdargs = '-p {prompt} -dmenu'.format(prompt=prompt)
        # allerrors = [(idx, e) for idx, e in enumerate(entries) if e.error]
        allerrors = []
        missings = []
        errors = []
        for e in allerrors:
            if isinstance(e[1].error, RequiredMissing):
                missings.append(str(e[0]))
            else:
                errors.append(str(e[0]))
        if errors:
            cmdargs += ' -u {idxs}'.format(idxs=','.join(errors))
        if missings:
            cmdargs += ' -a {idxs}'.format(idxs=','.join(missings))

        return '{cmd} {cmdargs}'.format(
            cmd=self.mp,
            cmdargs=cmdargs,
        )


dmenu = which('dmenu')
if dmenu:
    dmenump = DmenuMenuProvider(dmenu, 20)
    gsm.registerUtility(dmenump, IMenuProvider, 'dmenu')
rofi = which('rofi')
if rofi:
    rofimp = RofiMenuProvider(rofi, 30)
    gsm.registerUtility(rofimp, IMenuProvider, 'rofi')


def get_available_menu_providers():
    mps = getUtilitiesFor(IMenuProvider)
    mps = [(name, ut) for name, ut in mps]
    mps = sorted(mps, key=lambda x: x[1].priority, reverse=True)
    return mps


@implementer(IContextManager)
class Context(object):
    def selectinput(self, menu, prompt=None, filter_fnc=None):
        entries = [e for e in menu]
        prompt = prompt or menu.prompt
        if filter_fnc:
            entries = [e for e in filter(filter_fnc, entries)]
        try:
            choice = self.mp(entries, prompt=prompt)
        except SelectionNotValidError:
            return self.selectinput(
                menu, prompt=prompt, filter_fnc=filter_fnc)
        if choice:
            return choice

    def textinput(self, prompt=None):
        text = self.mp(entries=[], prompt=prompt)
        if text:
            return text


gsm.registerUtility(Context())


@implementer(II3Connector)
class I3Connector(object):

    def __init__(self):
        try:
            import i3ipc
            self.i3 = i3ipc.Connection()
        except:
            self.i3 = None
            logger.error('No i3wm connection found. Are you using i3?')

    def get_tree(self):
        return self.i3 and self.i3.get_tree() or None

    def get_workspaces(self):
        return self.i3 and self.i3.get_workspaces() or []

    def get_outputs(self):
        return self.i3 and self.i3.get_outputs() or []

    def get_windows(self):
        tree = self.get_tree()
        return tree and tree.leaves() or []

    def get_focused_window(self):
        tree = self.get_tree()
        return tree and tree.find_focused() or None

    def get_scratchpad_windows(self):
        return self.i3 and self.i3.get_tree().scratchpad().leaves() or []

    def get_focused_workspace(self):
        win = self.get_focused_window()
        return win and win.workspace() or None

    def get_active_outputs(self):
        outputs = self.get_outputs()
        active_outputs = []
        if outputs:
            active_outputs = [o for o in filter(lambda o: o.active, outputs)]
        return active_outputs

    def get_focused_output(self):
        ws = self.get_focused_workspace()
        return ws and ws.parent.parent or None

    def get_unfocused_outputs(self):
        active_outputs = self.get_active_outputs()
        focused_output = self.get_focused_output()
        active_outputs.pop(active_outputs.index(focused_output))
        return active_outputs

    def get_bar_ids(self):
        return self.i3 and self.i3.get_bar_config_list()

    def command(self, cmd):
        res = self.i3 and self.i3.command(cmd) or None
        return res


def get_connector():
    return I3Connector()

gsm = getGlobalSiteManager()
gsm.registerUtility(get_connector())
