from .. import loader, utils

import contextlib
import ast
import io
import gc


def insert_returns(body):
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])

    if isinstance(body[-1], ast.If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)

    if isinstance(body[-1], ast.With):
        insert_returns(body[-1].body)


async def async_eval(code: str, env: dict):
    code = code or "return"

    cmd = "\n".join(f"    {i}" for i in code.splitlines())
    body = f"async def _eval_temp():\n{cmd}"

    parsed = ast.parse(body)
    body = parsed.body[0].body

    insert_returns(body)

    env = {"__import__": __import__, **env}

    stdout = io.StringIO()
    stderr = io.StringIO()

    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            exec(compile(parsed, filename="<ast>", mode="exec"), env)
            result = await eval("_eval_temp()", env)
        except Exception:
            result = None

    return result, stdout.getvalue(), stderr.getvalue()


class EvalMod(loader.Module):
    @loader.command()
    async def eval(self, message, args):
        env = {
            "client": self.client,
            "message": message,
            "args": args,
        }

        result, stdout, stderr = None, None, None
        try:
            result, stdout, stderr = await async_eval(args.strip(), env)
            if callable(result):
                result = result.stringify()
        finally:
            gc.collect()

        std = (
            f"<b>STDOUT:</b>\n<code>{stdout}</code>\n"
            if stdout
            else "" f"<b>STDERR:</b>\n<code>{stderr}</code>\n" if stderr else ""
        )

        await utils.answer(
            message,
            (
                "<b>Code:</b>\n"
                f"<code>{args}</code>\n"
                "<b>Result:</b>\n"
                f"<code>{result}</code>\n"
            )
            + std,
        )
