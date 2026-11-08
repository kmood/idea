import argparse
from pathlib import Path

from .app import serve


def main():
    parser=argparse.ArgumentParser(description='Read-only local opportunity research dashboard.')
    parser.add_argument('--root',type=Path,default=Path.cwd())
    parser.add_argument('--db',type=Path,help='本机 records SQLite 路径；提供后开放私人操作')
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    if not 0<=args.port<=65535:parser.error('--port must be between 0 and 65535')
    serve(args.root,args.host,args.port,args.db)


if __name__=='__main__':main()
