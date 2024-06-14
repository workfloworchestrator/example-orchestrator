import re
from pathlib import Path

NETBOX_ROOT = Path('/opt/netbox/netbox')

resolve_reference = '''\
    @classmethod
    def resolve_reference(cls, id: strawberry.ID) -> '{type_name}':
        """Required for resolving this class through GraphQL Federation."""
        return models.{model_name}.objects.get(pk=id)
'''

type_directives = f"directives=[Key(fields=key, resolvable=UNSET) for key in ['id']],"


def insert_import(text: str, import_stmt: str) -> str:
    # Find the first import line and add our line above that
    return re.sub(r"(^(?:from .+|import .+)$)", rf"{import_stmt}\n\1", text, count=1, flags=re.MULTILINE)


def patch_types():
    file = NETBOX_ROOT / 'dcim/graphql/types.py'
    text = file.open().read()

    text = insert_import(text, "from strawberry.federation.schema_directives import Key")
    text = insert_import(text, "from strawberry import UNSET")
    types_to_patch = [
        ("Device", "DeviceType"),
    ]
    for model_name, type_name in types_to_patch:
        # Add resolve_reference() method to the class
        method = resolve_reference.format(type_name=type_name, model_name=model_name)
        regex_find_class = rf"(class {type_name}\(.+?\):\n)"
        text = re.sub(regex_find_class, rf"\1{method}\n", text, count=1, flags=re.DOTALL)

        # Add directives to the class decorator
        regex_find_decorator  = rf"(@strawberry_django.type\(\n\s+models\.{model_name},)"
        text = re.sub(regex_find_decorator, rf"\1 {type_directives}", text, count=1)

    with file.open(mode='w') as f:
        f.write(text)


def main():
    if not NETBOX_ROOT.is_dir():
        raise Exception(f"Netbox root {NETBOX_ROOT} not found")

    patch_types()


if __name__ == '__main__':
    main()
