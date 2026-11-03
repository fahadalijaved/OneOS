#!/usr/bin/env python3
"""Syntax-check the session scripts and every sh -c or su -c script embedded in them, at every
nesting level, with dash and busybox sh. Usage: scripts/check-shell.py switcher/assets/*.sh
(run 44: a quote in a comment inside the UI activator string passed dash -n on the file
but broke the activator itself)."""
import re, subprocess, sys, os, tempfile
def dq_unescape(s):
    out=[];i=0
    while i<len(s):
        c=s[i]
        if c=='\\' and i+1<len(s) and s[i+1] in '"$`\\\n':
            if s[i+1]!='\n': out.append(s[i+1])
            i+=2; continue
        out.append(c); i+=1
    return ''.join(out)
def extract(text):
    # find  sh -c "<body>"  and  sh -c '<body>', and su -c the same way: a
    # single-quoted su -c body is where an apostrophe in a comment closes the
    # quote and hands the rest of the script to the shell as nonsense
    # (scripts/pull-run-logs.sh, 2026-10-31). Reading the body as the shell
    # would catches it: what follows the stray quote no longer parses.
    res=[]
    for m in re.finditer(r'(?:sh|su) -c (["\'])', text):
        q=m.group(1); i=m.end(); j=i
        if q=="'":
            j=text.find("'",i);
            if j<0: continue
            # A stray apostrophe inside the body closes it early, and what the
            # shell then gets is the rest of the file as commands. The prefix
            # up to that quote usually still parses (a truncated script ending
            # in a comment does), so -n alone never sees it: check instead that
            # the body ends where an embedded script may end, which is at the
            # outer string's own quote or at the end of the command.
            nxt=text[j+1:j+2]
            if nxt not in ('"', '', '\n', ' ', '\t', ';', ')', '|', '&'):
                res.append(('!', "body closes early at an apostrophe (next character "
                                 f"{nxt!r}): a quote in a comment or word inside it ends the script",
                            m.start()))
                continue
            # A single-quoted body is usually nested in an outer double-quoted
            # string (adb shell "su -c '...'"), so it still carries that
            # context's backslash escapes; the shell sees them undone. On a
            # body that is not nested there is nothing to undo.
            res.append(("'",dq_unescape(text[i:j]),m.start())); continue
        while j<len(text):
            if text[j]=='\\': j+=2; continue
            if text[j]=='"': break
            j+=1
        res.append(('"',text[i:j],m.start()))
    return res
def check(body,label,depth,fails,total):
    total[0]+=1
    with tempfile.NamedTemporaryFile('w',suffix='.sh',delete=False) as f: f.write(body); fn=f.name
    for sh in (['dash','-n',fn],['busybox','sh','-n',fn]):
        r=subprocess.run(sh,capture_output=True,text=True)
        if r.returncode: fails.append(f"{label} depth{depth} [{sh[0]}]: {r.stderr.strip()[:200]}")
    os.unlink(fn)
    for q,b,pos in extract(body):
        if q=='!':
            fails.append(f"{label}@{pos}: {b}"); continue
        inner = dq_unescape(b) if q=='"' else b
        # outer variables appear as $NAME: harmless for -n
        check(inner,label+f"@{pos}",depth+1,fails,total)
fails=[];total=[0]
# No arguments: every session script (0.4.38: run without any, it checked nothing and said all parse,
# while a quote in a comment had cut the UI activator short, F8U test11).
paths = sys.argv[1:] or sorted(__import__('glob').glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'switcher', 'assets', '*.sh'))) + [
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app-android', 'app', 'src', 'full', 'assets', 'root', 'oneos_root.sh')]
for p in paths:
    t=open(p).read()
    for q,b,pos in extract(t):
        line=t.count('\n',0,pos)+1
        if q=='!':
            fails.append(f"{os.path.basename(p)}:{line}: {b}"); continue
        inner = dq_unescape(b) if q=='"' else b
        check(inner,f"{os.path.basename(p)}:{line}",1,fails,total)
print(f"embedded scripts checked: {total[0]}"); print("\n".join(fails) if fails else "all parse in dash and busybox")
