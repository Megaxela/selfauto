async def check_tasks_results_error(results, logger=None):
    failed = False
    for result in results:
        if isinstance(result, Exception):
            failed = True
            if logger is not None:
                logger(result)
    return not failed
