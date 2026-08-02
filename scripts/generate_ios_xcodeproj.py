#!/usr/bin/env python3
"""生成 ios/CarrierTakeOff.xcodeproj（无需 XcodeGen）。"""
from __future__ import annotations

import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IOS = ROOT / 'ios'
SRC = IOS / 'CarrierTakeOff'
PROJ = IOS / 'CarrierTakeOff.xcodeproj'


def _id(name: str) -> str:
    """稳定 24 位十六进制 ID（基于名称，便于 diff）。"""
    return uuid.uuid5(uuid.NAMESPACE_URL, f'carrier-takeoff-ios:{name}').hex[:24].upper()


def main() -> None:
    """写出 project.pbxproj。"""
    swift_files = sorted(p.relative_to(SRC) for p in SRC.rglob('*.swift'))
    asset_dirs = sorted(
        p.relative_to(SRC)
        for p in SRC.rglob('*.xcassets')
        if p.is_dir()
    )
    data_json = SRC / 'Resources' / 'data.json'
    info_plist = SRC / 'Info.plist'
    assert data_json.is_file(), '缺少 data.json，请先运行 build_all.py'
    assert info_plist.is_file()

    resource_files = sorted(
        p.relative_to(SRC)
        for p in (SRC / 'Resources').iterdir()
        if p.is_file()
    )

    project_id = _id('project')
    target_id = _id('target')
    sources_phase = _id('sources')
    resources_phase = _id('resources')
    frameworks_phase = _id('frameworks')
    product_ref = _id('product')
    main_group = _id('main_group')
    products_group = _id('products_group')
    src_group = _id('src_group')
    components_group = _id('components_group')
    resources_group = _id('resources_group')
    assets_group = _id('assets')
    config_list_proj = _id('cfglist_proj')
    config_list_tgt = _id('cfglist_tgt')
    cfg_proj_debug = _id('cfg_proj_debug')
    cfg_proj_release = _id('cfg_proj_release')
    cfg_tgt_debug = _id('cfg_tgt_debug')
    cfg_tgt_release = _id('cfg_tgt_release')

    file_refs: dict[str, str] = {}
    build_files: dict[str, str] = {}

    for rel in swift_files:
        key = str(rel)
        file_refs[key] = _id(f'file:{key}')
        build_files[key] = _id(f'build:{key}')

    for rel in resource_files:
        key = str(rel)
        file_refs[key] = _id(f'file:{key}')
        build_files[key] = _id(f'build:{key}')

    for rel in asset_dirs:
        key = str(rel)
        file_refs[key] = _id(f'file:{key}')
        build_files[key] = _id(f'build:{key}')

    file_refs['Info.plist'] = _id('file:Info.plist')

    lines: list[str] = []
    lines.append('// !$*UTF8*$!')
    lines.append('{')
    lines.append('\tarchiveVersion = 1;')
    lines.append('\tclasses = {};')
    lines.append('\tobjectVersion = 56;')
    lines.append('\tobjects = {')

    # PBXBuildFile
    lines.append('\n/* Begin PBXBuildFile section */')
    for key, bid in build_files.items():
        ref = file_refs[key]
        lines.append(f'\t\t{bid} /* {key} in Sources/Resources */ = {{isa = PBXBuildFile; fileRef = {ref} /* {key} */; }};')
    lines.append('/* End PBXBuildFile section */\n')

    # PBXFileReference
    lines.append('/* Begin PBXFileReference section */')
    lines.append(
        f'\t\t{product_ref} /* CarrierTakeOff.app */ = {{isa = PBXFileReference; explicitFileType = wrapper.application; includeInIndex = 0; path = CarrierTakeOff.app; sourceTree = BUILT_PRODUCTS_DIR; }};'
    )
    for rel in swift_files:
        key = str(rel)
        lines.append(
            f'\t\t{file_refs[key]} /* {key} */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = "{Path(key).name}"; sourceTree = "<group>"; }};'
        )
    for rel in resource_files:
        key = str(rel)
        name = Path(key).name
        if name.endswith('.json'):
            ftype = 'text.json'
        elif name.endswith('.js'):
            ftype = 'sourcecode.javascript'
        elif name.endswith('.html'):
            ftype = 'text.html'
        else:
            ftype = 'text'
        lines.append(
            f'\t\t{file_refs[key]} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = {ftype}; path = {name}; sourceTree = "<group>"; }};'
        )
    for rel in asset_dirs:
        key = str(rel)
        lines.append(
            f'\t\t{file_refs[key]} /* {key} */ = {{isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; path = "{Path(key).name}"; sourceTree = "<group>"; }};'
        )
    lines.append(
        f'\t\t{file_refs["Info.plist"]} /* Info.plist */ = {{isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>"; }};'
    )
    lines.append('/* End PBXFileReference section */\n')

    # Groups
    root_swifts = [str(p) for p in swift_files if len(Path(p).parts) == 1]
    component_swifts = [str(p) for p in swift_files if Path(p).parts[0] == 'Components']

    lines.append('/* Begin PBXGroup section */')
    lines.append(f'\t\t{main_group} = {{')
    lines.append('\t\t\tisa = PBXGroup;')
    lines.append('\t\t\tchildren = (')
    lines.append(f'\t\t\t\t{src_group} /* CarrierTakeOff */,')
    lines.append(f'\t\t\t\t{products_group} /* Products */,')
    lines.append('\t\t\t);')
    lines.append('\t\t\tsourceTree = "<group>";')
    lines.append('\t\t};')

    lines.append(f'\t\t{products_group} /* Products */ = {{')
    lines.append('\t\t\tisa = PBXGroup;')
    lines.append('\t\t\tchildren = (')
    lines.append(f'\t\t\t\t{product_ref} /* CarrierTakeOff.app */,')
    lines.append('\t\t\t);')
    lines.append('\t\t\tname = Products;')
    lines.append('\t\t\tsourceTree = "<group>";')
    lines.append('\t\t};')

    lines.append(f'\t\t{src_group} /* CarrierTakeOff */ = {{')
    lines.append('\t\t\tisa = PBXGroup;')
    lines.append('\t\t\tchildren = (')
    for key in root_swifts:
        lines.append(f'\t\t\t\t{file_refs[key]} /* {key} */,')
    lines.append(f'\t\t\t\t{components_group} /* Components */,')
    lines.append(f'\t\t\t\t{resources_group} /* Resources */,')
    for rel in asset_dirs:
        key = str(rel)
        lines.append(f'\t\t\t\t{file_refs[key]} /* {key} */,')
    lines.append(f'\t\t\t\t{file_refs["Info.plist"]} /* Info.plist */,')
    lines.append('\t\t\t);')
    lines.append('\t\t\tpath = CarrierTakeOff;')
    lines.append('\t\t\tsourceTree = "<group>";')
    lines.append('\t\t};')

    lines.append(f'\t\t{components_group} /* Components */ = {{')
    lines.append('\t\t\tisa = PBXGroup;')
    lines.append('\t\t\tchildren = (')
    for key in component_swifts:
        lines.append(f'\t\t\t\t{file_refs[key]} /* {key} */,')
    lines.append('\t\t\t);')
    lines.append('\t\t\tpath = Components;')
    lines.append('\t\t\tsourceTree = "<group>";')
    lines.append('\t\t};')

    lines.append(f'\t\t{resources_group} /* Resources */ = {{')
    lines.append('\t\t\tisa = PBXGroup;')
    lines.append('\t\t\tchildren = (')
    for rel in resource_files:
        key = str(rel)
        lines.append(f'\t\t\t\t{file_refs[key]} /* {Path(key).name} */,')
    lines.append('\t\t\t);')
    lines.append('\t\t\tpath = Resources;')
    lines.append('\t\t\tsourceTree = "<group>";')
    lines.append('\t\t};')
    lines.append('/* End PBXGroup section */\n')

    # Native target
    lines.append('/* Begin PBXNativeTarget section */')
    lines.append(f'\t\t{target_id} /* CarrierTakeOff */ = {{')
    lines.append('\t\t\tisa = PBXNativeTarget;')
    lines.append(f'\t\t\tbuildConfigurationList = {config_list_tgt} /* Build configuration list for PBXNativeTarget "CarrierTakeOff" */;')
    lines.append('\t\t\tbuildPhases = (')
    lines.append(f'\t\t\t\t{sources_phase} /* Sources */,')
    lines.append(f'\t\t\t\t{frameworks_phase} /* Frameworks */,')
    lines.append(f'\t\t\t\t{resources_phase} /* Resources */,')
    lines.append('\t\t\t);')
    lines.append('\t\t\tbuildRules = (')
    lines.append('\t\t\t);')
    lines.append('\t\t\tdependencies = (')
    lines.append('\t\t\t);')
    lines.append('\t\t\tname = CarrierTakeOff;')
    lines.append(f'\t\t\tproductName = CarrierTakeOff;')
    lines.append(f'\t\t\tproductReference = {product_ref} /* CarrierTakeOff.app */;')
    lines.append('\t\t\tproductType = "com.apple.product-type.application";')
    lines.append('\t\t};')
    lines.append('/* End PBXNativeTarget section */\n')

    # Project
    lines.append('/* Begin PBXProject section */')
    lines.append(f'\t\t{project_id} /* Project object */ = {{')
    lines.append('\t\t\tisa = PBXProject;')
    lines.append('\t\t\tattributes = {')
    lines.append('\t\t\t\tBuildIndependentTargetsInParallel = 1;')
    lines.append('\t\t\t\tLastSwiftUpdateCheck = 1500;')
    lines.append('\t\t\t\tLastUpgradeCheck = 1500;')
    lines.append('\t\t\t};')
    lines.append(f'\t\t\tbuildConfigurationList = {config_list_proj} /* Build configuration list for PBXProject "CarrierTakeOff" */;')
    lines.append('\t\t\tcompatibilityVersion = "Xcode 14.0";')
    lines.append('\t\t\tdevelopmentRegion = "zh-Hans";')
    lines.append('\t\t\thasScannedForEncodings = 0;')
    lines.append('\t\t\tknownRegions = (')
    lines.append('\t\t\t\ten,')
    lines.append('\t\t\t\tBase,')
    lines.append('\t\t\t\t"zh-Hans",')
    lines.append('\t\t\t);')
    lines.append(f'\t\t\tmainGroup = {main_group};')
    lines.append(f'\t\t\tproductRefGroup = {products_group} /* Products */;')
    lines.append('\t\t\tprojectDirPath = "";')
    lines.append('\t\t\tprojectRoot = "";')
    lines.append('\t\t\ttargets = (')
    lines.append(f'\t\t\t\t{target_id} /* CarrierTakeOff */,')
    lines.append('\t\t\t);')
    lines.append('\t\t};')
    lines.append('/* End PBXProject section */\n')

    # Sources / Resources / Frameworks
    lines.append('/* Begin PBXSourcesBuildPhase section */')
    lines.append(f'\t\t{sources_phase} /* Sources */ = {{')
    lines.append('\t\t\tisa = PBXSourcesBuildPhase;')
    lines.append('\t\t\tbuildActionMask = 2147483647;')
    lines.append('\t\t\tfiles = (')
    for key in [str(p) for p in swift_files]:
        lines.append(f'\t\t\t\t{build_files[key]} /* {key} in Sources */,')
    lines.append('\t\t\t);')
    lines.append('\t\t\trunOnlyForDeploymentPostprocessing = 0;')
    lines.append('\t\t};')
    lines.append('/* End PBXSourcesBuildPhase section */\n')

    lines.append('/* Begin PBXResourcesBuildPhase section */')
    lines.append(f'\t\t{resources_phase} /* Resources */ = {{')
    lines.append('\t\t\tisa = PBXResourcesBuildPhase;')
    lines.append('\t\t\tbuildActionMask = 2147483647;')
    lines.append('\t\t\tfiles = (')
    for rel in resource_files:
        key = str(rel)
        lines.append(f'\t\t\t\t{build_files[key]} /* {Path(key).name} in Resources */,')
    for rel in asset_dirs:
        key = str(rel)
        lines.append(f'\t\t\t\t{build_files[key]} /* {key} in Resources */,')
    lines.append('\t\t\t);')
    lines.append('\t\t\trunOnlyForDeploymentPostprocessing = 0;')
    lines.append('\t\t};')
    lines.append('/* End PBXResourcesBuildPhase section */\n')

    lines.append('/* Begin PBXFrameworksBuildPhase section */')
    lines.append(f'\t\t{frameworks_phase} /* Frameworks */ = {{')
    lines.append('\t\t\tisa = PBXFrameworksBuildPhase;')
    lines.append('\t\t\tbuildActionMask = 2147483647;')
    lines.append('\t\t\tfiles = (')
    lines.append('\t\t\t);')
    lines.append('\t\t\trunOnlyForDeploymentPostprocessing = 0;')
    lines.append('\t\t};')
    lines.append('/* End PBXFrameworksBuildPhase section */\n')

    # XCBuildConfiguration
    common_tgt = '''
				ASSETCATALOG_COMPILER_GENERATE_SWIFT_ASSET_SYMBOL_EXTENSIONS = YES;
				CODE_SIGN_STYLE = Automatic;
				CURRENT_PROJECT_VERSION = 1;
				DEVELOPMENT_TEAM = "";
				GENERATE_INFOPLIST_FILE = NO;
				INFOPLIST_FILE = CarrierTakeOff/Info.plist;
				IPHONEOS_DEPLOYMENT_TARGET = 17.0;
				LD_RUNPATH_SEARCH_PATHS = (
					"$(inherited)",
					"@executable_path/Frameworks",
				);
				MARKETING_VERSION = 1.0;
				PRODUCT_BUNDLE_IDENTIFIER = com.carriertakeoff.simulator;
				PRODUCT_NAME = "$(TARGET_NAME)";
				SDKROOT = iphoneos;
				SUPPORTED_PLATFORMS = "iphoneos iphonesimulator";
				SUPPORTS_MACCATALYST = NO;
				SWIFT_EMIT_LOC_STRINGS = YES;
				SWIFT_VERSION = 5.0;
				TARGETED_DEVICE_FAMILY = "1,2";
'''

    lines.append('/* Begin XCBuildConfiguration section */')
    for cfg_id, name, extra in (
        (cfg_proj_debug, 'Debug', '\t\t\t\tDEBUG_INFORMATION_FORMAT = dwarf;\n\t\t\t\tSWIFT_OPTIMIZATION_LEVEL = "-Onone";\n\t\t\t\tONLY_ACTIVE_ARCH = YES;\n\t\t\t\tGCC_PREPROCESSOR_DEFINITIONS = ("DEBUG=1", "$(inherited)",);\n'),
        (cfg_proj_release, 'Release', '\t\t\t\tDEBUG_INFORMATION_FORMAT = "dwarf-with-dsym";\n\t\t\t\tSWIFT_COMPILATION_MODE = wholemodule;\n'),
    ):
        lines.append(f'\t\t{cfg_id} /* {name} */ = {{')
        lines.append('\t\t\tisa = XCBuildConfiguration;')
        lines.append('\t\t\tbuildSettings = {')
        lines.append('\t\t\t\tALWAYS_SEARCH_USER_PATHS = NO;')
        lines.append('\t\t\t\tCLANG_ENABLE_MODULES = YES;')
        lines.append('\t\t\t\tCLANG_ENABLE_OBJC_ARC = YES;')
        lines.append('\t\t\t\tCOPY_PHASE_STRIP = NO;')
        lines.append(extra.rstrip('\n'))
        lines.append('\t\t\t\tIPHONEOS_DEPLOYMENT_TARGET = 17.0;')
        lines.append('\t\t\t\tSDKROOT = iphoneos;')
        lines.append('\t\t\t};')
        lines.append(f'\t\t\tname = {name};')
        lines.append('\t\t};')

    for cfg_id, name in ((cfg_tgt_debug, 'Debug'), (cfg_tgt_release, 'Release')):
        lines.append(f'\t\t{cfg_id} /* {name} */ = {{')
        lines.append('\t\t\tisa = XCBuildConfiguration;')
        lines.append('\t\t\tbuildSettings = {')
        lines.append(common_tgt.rstrip('\n'))
        if name == 'Debug':
            lines.append('\t\t\t\tSWIFT_OPTIMIZATION_LEVEL = "-Onone";')
        lines.append('\t\t\t};')
        lines.append(f'\t\t\tname = {name};')
        lines.append('\t\t};')
    lines.append('/* End XCBuildConfiguration section */\n')

    lines.append('/* Begin XCConfigurationList section */')
    lines.append(f'\t\t{config_list_proj} /* Build configuration list for PBXProject "CarrierTakeOff" */ = {{')
    lines.append('\t\t\tisa = XCConfigurationList;')
    lines.append('\t\t\tbuildConfigurations = (')
    lines.append(f'\t\t\t\t{cfg_proj_debug} /* Debug */,')
    lines.append(f'\t\t\t\t{cfg_proj_release} /* Release */,')
    lines.append('\t\t\t);')
    lines.append('\t\t\tdefaultConfigurationIsVisible = 0;')
    lines.append('\t\t\tdefaultConfigurationName = Release;')
    lines.append('\t\t};')
    lines.append(f'\t\t{config_list_tgt} /* Build configuration list for PBXNativeTarget "CarrierTakeOff" */ = {{')
    lines.append('\t\t\tisa = XCConfigurationList;')
    lines.append('\t\t\tbuildConfigurations = (')
    lines.append(f'\t\t\t\t{cfg_tgt_debug} /* Debug */,')
    lines.append(f'\t\t\t\t{cfg_tgt_release} /* Release */,')
    lines.append('\t\t\t);')
    lines.append('\t\t\tdefaultConfigurationIsVisible = 0;')
    lines.append('\t\t\tdefaultConfigurationName = Release;')
    lines.append('\t\t};')
    lines.append('/* End XCConfigurationList section */')

    lines.append('\t};')
    lines.append(f'\trootObject = {project_id} /* Project object */;')
    lines.append('}')

    PROJ.mkdir(parents=True, exist_ok=True)
    out = PROJ / 'project.pbxproj'
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'Wrote {out}')


if __name__ == '__main__':
    main()
