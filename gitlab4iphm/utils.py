import requests

session = None


def perform_request(url, method, data={}, params={}, headers={}, dry_run=False):
    '''
    Utility method to perform an HTTP request.
    '''
    if dry_run and method != "get":
        msg = "{} {} dry_run".format(url, method)
        print(msg)
        return 0

    global session
    if not session:
        session = requests.Session()

    func = getattr(session, method)
    result = func(url, params=params, data=data, headers=headers)

    if result.status_code in [200, 201]:
        return result.headers, result.json()

    raise Exception("{} failed requests: {}".format(result.status_code, result.reason))
