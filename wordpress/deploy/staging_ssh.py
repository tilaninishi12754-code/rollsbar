"""Staging transport primitives; never retry a mutating exec request."""
import os
import posixpath
import re
import stat
from urllib.parse import urlsplit

RUNTIME_FILE = '.rollsbar-staging-runtime.env'


def connect():
    import paramiko
    host = urlsplit(os.environ['ISP_MANAGER_URL']).hostname
    if not host:
        raise ValueError('Missing staging SSH host')
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(hostname=host, username=os.environ['ISP_MANAGER_USER'],
                       password=os.environ['ISP_MANAGER_PASSWORD'], timeout=15,
                       auth_timeout=15, banner_timeout=15, look_for_keys=False, allow_agent=False)
    except Exception:
        client.close()
        raise
    return client


def metadata(sftp, path):
    try:
        info = sftp.lstat(path)
    except FileNotFoundError:
        return {'exists': False}
    return {'exists': True, 'regular': stat.S_ISREG(info.st_mode),
            'symlink': stat.S_ISLNK(info.st_mode), 'mode': oct(stat.S_IMODE(info.st_mode)),
            'size': info.st_size}


def allowed_name(name):
    return name == RUNTIME_FILE or bool(re.fullmatch(r'\.rollsbar-staging-deploy-[0-9a-f]{32}\.sh', name))


def safe_path(sftp, name):
    if not allowed_name(name) or posixpath.basename(name) != name:
        raise ValueError('Refusing unexpected temporary basename')
    home = sftp.normalize('.')
    if not home.startswith('/') or home == '/':
        raise ValueError('Refusing unexpected authenticated home')
    return posixpath.join(home, name)


def write_new(sftp, name, body, mode, created):
    path = safe_path(sftp, name)
    # Exclusive create prevents overwriting an earlier run or following a link.
    with sftp.open(path, 'wx') as stream:
        created.append(name)
        sftp.chmod(path, mode)
        stream.write(body)


def cleanup_files(names, connector=connect):
    """Fresh authenticated SFTP only; lstat/remove/lstat, never read contents."""
    receipts = []
    client = connector()
    try:
        sftp = client.open_sftp()
        try:
            errors = []
            for name in names:
                row = {'name': name}
                try:
                    path = safe_path(sftp, name)
                    row['before'] = metadata(sftp, path)
                    if row['before']['exists']:
                        expected = '0o600' if name == RUNTIME_FILE else '0o700'
                        if (not row['before']['regular'] or row['before']['symlink']
                                or row['before']['mode'] != expected):
                            raise ValueError('Refusing unexpected temporary object')
                        sftp.remove(path)
                    row['after'] = metadata(sftp, path)
                    if row['after']['exists']:
                        raise RuntimeError('Temporary file remains after cleanup')
                except Exception as exc:
                    row['error_type'] = type(exc).__name__
                    errors.append(name)
                receipts.append(row)
            if errors:
                raise RuntimeError('Independent cleanup failed for ' + ','.join(errors))
        finally:
            sftp.close()
    finally:
        client.close()
        # Names and metadata only; no secret body or exception message.
        import json
        print('temporary_cleanup=' + json.dumps(receipts), flush=True)
    return receipts


def probe(connector=connect):
    client = connector()
    try:
        _, out, err = client.exec_command("printf 'SSH_EXEC_OK\\n'", timeout=20)
        body = out.read()
        err.read()
        if out.channel.recv_exit_status() != 0 or body.strip() != b'SSH_EXEC_OK':
            raise RuntimeError('Fresh exec probe failed')
        print('SSH_EXEC_OK', flush=True)
    finally:
        client.close()
