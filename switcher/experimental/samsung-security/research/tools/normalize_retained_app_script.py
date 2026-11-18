"""Pin runnable LF bytes for the selected local Android shell asset, without execution."""
from pathlib import Path
import hashlib, json, subprocess

ROOT = Path(__file__).resolve().parents[1]
CLONE = ROOT/'firmware/oneos-pr/OneOS'
RELATIVE = 'app-android/app/src/full/assets/root/oneos_root.sh'
RAW_SHA = '4cdaa8af50b7b524bbf60e178ab6a14903174d60af4181ec273b6006aa1373ba'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def main():
    base = subprocess.check_output(['git', 'show', '93c6da8053e3494b8732bc359b2095319ff93b6a:'+RELATIVE], cwd=CLONE)
    # This is the original public Git blob, rather than a Windows checkout's EOLs.
    assert b'\r' not in base
    path = CLONE/RELATIVE
    raw = path.read_bytes()
    history = ROOT/'out/full-app-integration/rootsh-before-lf-normalization.sh'
    if sha(raw) == RAW_SHA:
        normalized = raw.replace(b'\r\n', b'\n')
        assert b'\r' not in normalized
        history.parent.mkdir(parents=True, exist_ok=True)
        if history.exists():
            assert history.read_bytes() == raw
        else:
            history.write_bytes(raw)
        path.write_bytes(normalized)
    else:
        assert history.is_file() and sha(history.read_bytes()) == RAW_SHA
        normalized = history.read_bytes().replace(b'\r\n', b'\n')
        assert raw == normalized
    # A scoped checkout rule makes this reproducible without changing global Git.
    attributes = CLONE/'.gitattributes'
    rule = (RELATIVE+' text eol=lf\n').encode()
    # The supported native recipe pins original authored source bytes, including
    # their EOLs. Preserve these two inputs in Git on every checkout platform.
    native_rules = (b'switcher/native/retained_root_session.c -text\n'
                    b'switcher/native/retained_root_session_protocol.h -text\n')
    base_attributes = subprocess.check_output(['git', 'show', '93c6da8053e3494b8732bc359b2095319ff93b6a:.gitattributes'], cwd=CLONE)
    previous_attributes = base_attributes.rstrip(b'\n') + b'\n' + rule
    expected_attributes = previous_attributes + native_rules
    current_attributes = attributes.read_bytes()
    assert current_attributes in (base_attributes, base_attributes.replace(b'\n', b'\r\n'), previous_attributes, expected_attributes)
    if current_attributes != expected_attributes:
        (ROOT/'out/full-app-integration/gitattributes-before-current-rules').write_bytes(current_attributes)
        attributes.write_bytes(expected_attributes)
    result = {'status': 'SOURCE_EOL_NORMALIZATION_ONLY', 'asset': RELATIVE,
              'rawSha256': RAW_SHA, 'rawBytes': len(history.read_bytes()),
              'runnableLfSha256': sha(normalized), 'runnableLfBytes': len(normalized),
              'publicBaseBlobSha256': sha(base), 'publicBaseBlobBytes': len(base),
              'onlyCrlfToLf': normalized == history.read_bytes().replace(b'\r\n', b'\n'),
              'nativeSourceBytesPreservedByScopedAttributes': True,
              'globalGitSettingsChanged': False, 'scriptExecuted': False}
    (ROOT/'out/full-app-integration/rootsh-lf-normalization.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
