from .. import loader, utils


class HelpMod(loader.Module):
    @loader.command()
    async def helpcmd(self, message):
        modules = self.loader.modules
        all_text = ""

        for module in modules:
            module_name = module.__class__.__name__
            if module_name == "HelpMod":
                continue

            commands = ", ".join(
                f"<code>{cmd}</code>" for cmd in module.commands.keys()
            )
            text = f"<b>☕ {module_name}:</b> {commands}"

            all_text += text + "\n"

        await utils.answer(message, all_text)
