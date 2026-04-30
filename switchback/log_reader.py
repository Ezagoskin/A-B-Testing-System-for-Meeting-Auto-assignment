import argparse
import json

def load_and_filter(logpath, filter_str, getter_str):
    result = []
    with open(logpath) as file:
        for line in file:
            log = json.loads(line) 

            if eval(filter_str):
               result.append(eval(getter_str)) 

    print(f'found {len(result)} logs')
    print('\n\n'.join(result))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('logpath')
    parser.add_argument('filter')
    parser.add_argument('getter')

    args = parser.parse_args()

    load_and_filter(args.logpath, args.filter, args.getter)

if __name__ == '__main__':
    main()
