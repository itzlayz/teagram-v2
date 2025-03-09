from .. import loader, utils


class Help(loader.Module):
    strings = {"name": "Help"}

    @loader.command()
    async def helpcmd(self, message, args):
        modules = self.loader.modules
        all_text = self.get("modules")

        core = False
        if args and any([arg in args for arg in ("--core", "-c")]):
            core = True

        for module in modules:
            module_name = module.__class__.__name__
            origin = module.__origin__

            if module_name == "HelpMod":
                continue

            if core and origin != "<core>":
                continue

            smile = "📦" if origin != "<core>" else "🔧"

            commands = " | ".join(
                f"<code>{cmd}</code>" for cmd in module.commands.keys()
            )
            text = f"<b>{smile} {module_name}:</b> {commands}"

            all_text += text + "\n"

        await utils.answer(message, all_text)
