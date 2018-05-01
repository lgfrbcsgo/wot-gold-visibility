#!/usr/bin/env python2.7

import re
import os
from argparse import ArgumentParser
from zipfile import ZipFile, ZIP_DEFLATED

out_dir = './out'
color_out_file = 'goldvisibility.color.wotmod'
core_out_file = 'goldvisibility.core.wotmod'


def find_dependents(zip, dependency_regex, entry_points, targets):
    from networkx import DiGraph
    from networkx.algorithms.simple_paths import all_simple_paths

    nodes = zip.namelist()
    dependency_graph = DiGraph()
    dependency_graph.add_nodes_from(nodes)

    for node in nodes:
        with zip.open(node, 'r') as zipped_file:
            content = zipped_file.read()
            for match in dependency_regex.finditer(content):
                dependency_graph.add_edge(node, match.group())

    dependents = set()
    actual_targets = set()

    for source in entry_points:
        for target in targets:
            for path in all_simple_paths(dependency_graph, source, target):
                actual_targets.add(path[-1])
                for dependent in path[0:-1]:
                    dependents.add(dependent)

    return list(dependents), list(actual_targets)


# https://stackoverflow.com/questions/8627835/generate-pyc-from-python-ast
def make_bytecode(code, file_name):
    import time
    import marshal
    import py_compile

    code_obj = compile(code, file_name, 'exec')
    timestamp = long(time.time())
    bytecode = py_compile.MAGIC
    bytecode += chr(timestamp & 0xff)
    bytecode += chr((timestamp >> 8) & 0xff)
    bytecode += chr((timestamp >> 16) & 0xff)
    bytecode += chr((timestamp >> 24) & 0xff)
    bytecode += marshal.dumps(code_obj)
    return bytecode


def make_prereqs_module(file_paths):
    def resolve_file_name(file_path):
        if file_path.endswith('.bin'):
            return file_path[:-4] + '.xml'
        return file_path

    code = 'files=["' + '","'.join(map(resolve_file_name, file_paths)) + '"]'
    base_name = 'scripts/client/gui/mods/goldvisibility_prereqs'
    return base_name + '.pyc', make_bytecode(code, base_name + '.py')


def make_main_module():
    base_name = 'scripts/client/gui/mods/mod_goldvisibility'
    with open('src/' + base_name + '.py', 'r') as file:
        return base_name + '.pyc', make_bytecode(file.read(), base_name + '.py')


def make_effects_file(zip, file_path, dependency_regex, filtered_dependencies):
    with zip.open(file_path, 'r') as zipped_file:
        content = zipped_file.read()
        for match in dependency_regex.finditer(content):
            dependency = match.group()
            if dependency in filtered_dependencies and content[match.end(): match.end() + 5] == (b'\x00' * 5):
                base_name, extension = dependency.rsplit('.', 1)
                content = content[:match.start()] + base_name + b'_prem.' + extension + content[match.end() + 5:]
        base_name, extension = file_path.rsplit('.', 1)
        return base_name + '_prem.' + extension, content


def make_texture(zip, file_path, color_code):
    from wand.image import Image

    red = int(color_code[:2], 16) / 255.0
    green = int(color_code[2:4], 16) / 255.0
    blue = int(color_code[4:], 16) / 255.0

    base_name, extension = file_path.rsplit('.', 1)

    with zip.open(file_path, 'r') as zipped_file:
        with Image(file=zipped_file, format=extension) as img:
            img.threshold(-1, 'red')
            img.threshold(-1, 'green')
            img.threshold(-1, 'blue')
            img.evaluate('multiply', red, channel='red')
            img.evaluate('multiply', green, channel='green')
            img.evaluate('multiply', blue, channel='blue')
            return base_name + '_prem.' + extension, img.make_blob()


def make_goldvisibility_core(particles_pkg_path):
    out_file = os.path.join(out_dir, core_out_file)
    try:
        os.remove(out_file)
    except OSError:
        pass

    with ZipFile(particles_pkg_path, 'r') as zip:
        with ZipFile(out_file, 'w') as out:
            entry_point_regex = re.compile('particles/Shells_Eff/[a-zA-Z0-9_\-.]+\.[a-zA-Z0-9_\-.]+')
            entry_points = [file_name for file_name in zip.namelist() if entry_point_regex.match(file_name) is not None]

            textures = [
                'particles/content_forward/PFX_textures/eff_tex.dds',
                'particles/content_deferred/PFX_textures/eff_tex.dds'
            ]

            dependency_regex = re.compile(b'particles(\/[a-zA-Z0-9_\-.]+)+\.[a-zA-Z0-9_\-.]+')
            dependents, targets = find_dependents(zip, dependency_regex, entry_points, textures)
            dependencies = dependents + targets

            prereqs = [
                'particles/content_forward/PFX_textures/eff_tex_prem.dds',
                'particles/content_deferred/PFX_textures/eff_tex_prem.dds'
            ]

            for dependent in dependents:
                file_name, content = make_effects_file(zip, dependent, dependency_regex, dependencies)
                prereqs.append(file_name)
                out.writestr('res/' + file_name, content)

            file_name, content = make_prereqs_module(prereqs)
            out.writestr('res/' + file_name, content)

            file_name, content = make_main_module()
            out.writestr('res/' + file_name, content)


def make_goldvisibility_color(particles_pkg_path, color_code):
    out_file = os.path.join(out_dir, color_out_file)
    try:
        os.remove(out_file)
    except OSError:
        pass

    with ZipFile(particles_pkg_path, 'r') as zip:
        with ZipFile(out_file, 'w') as out:

            textures = [
                'particles/content_forward/PFX_textures/eff_tex.dds',
                'particles/content_deferred/PFX_textures/eff_tex.dds'
            ]

            for texture in textures:
                file_name, content = make_texture(zip, texture, color_code)
                out.writestr('res/' + file_name, content)


def make_package(particles_pkg_path, version, name, color_code, rebuild_core):
    if rebuild_core or not os.path.isfile(os.path.join(out_dir, core_out_file)):
        make_goldvisibility_core(particles_pkg_path)
    make_goldvisibility_color(particles_pkg_path, color_code)

    out_file = os.path.join(out_dir, name)
    try:
        os.remove(out_file)
    except OSError:
        pass

    with ZipFile(out_file, 'w', ZIP_DEFLATED) as zip:
        core_path = os.path.join(out_dir, core_out_file)
        core_zip_path = os.path.join('mods', version, core_out_file)
        zip.write(core_path, core_zip_path)

        color_path = os.path.join(out_dir, color_out_file)
        color_zip_path = os.path.join('mods', version, color_out_file)
        zip.write(color_path, color_zip_path)

        # https://stackoverflow.com/questions/18394147/recursive-sub-folder-search-and-return-files-in-a-list-python
        def get_other_files(directory):
            return [os.path.join(dp, f) for dp, dn, filenames in os.walk(directory) for f in filenames]

        other_files = get_other_files('mods') + get_other_files('res_mods')
        for file in other_files:
            zip.write(file)


def main():
    parser = ArgumentParser()
    parser.add_argument('particles_pkg_path')
    subparsers = parser.add_subparsers(dest='subparser_name')

    core_parser = subparsers.add_parser('core')

    color_parser = subparsers.add_parser('color')
    color_parser.add_argument('color_code')

    package_parser = subparsers.add_parser('package')
    package_parser.add_argument('wot_version')
    package_parser.add_argument('package_name')
    package_parser.add_argument('color_code')
    package_parser.add_argument('-r', '--rebuild_core', action='store_true')

    args = parser.parse_args()

    try:
        os.makedirs(out_dir)
    except OSError:
        pass

    if args.subparser_name == 'core':
        make_goldvisibility_core(args.particles_pkg_path)

    elif args.subparser_name == 'color':
        make_goldvisibility_color(args.particles_pkg_path, args.color_code)

    elif args.subparser_name == 'package':
        make_package(args.particles_pkg_path, args.wot_version, args.package_name, args.color_code, args.rebuild_core)


if __name__ == "__main__":
    main()
