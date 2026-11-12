# Signing In to the Lab Tools

Your lab has several tools with web pages: Gitea, Mattermost, Grafana, Keycloak and Argo CD. Each page asks for a username and password. You do not have to remember or type them. Copy a command, paste it in your terminal, and it prints the sign-in for that tool.

## Before you start

1. Connect to the lab server with the address and key your instructor gave you.
2. Open the lab shell:

```
lab shell
```

3. Your prompt changes to `bash-5.1$`. Run every command in this guide at that prompt.

You never need a password for `oc`, `kubectl`, `git` through the lab, or any other command-line tool inside the lab shell. You are already signed in to your cluster. Check it:

```
oc whoami
```

It prints `system:admin`.

## Step 1. Get the address of each tool

Paste this to print every address in one go:

```
echo "Gitea:      $GITEA_URL"
echo "Mattermost: $MM_URL"
echo "Grafana:    $GRAFANA_URL"
echo "Keycloak:   $KEYCLOAK_URL"
echo "Argo CD:    $ARGOCD_URL"
```

Copy an address into your web browser.

## Step 2. Get the username and password for the tool

Each block prints the username first, then the password. Each prints on its own line.

### Gitea (your Git server)

```
echo "$GITEA_USER"
oc get secret gitea-admin -n gitea -o jsonpath='{.data.password}' | base64 -d; echo
```

### Mattermost (team chat)

```
oc get secret mattermost-admin -n chat -o jsonpath='{.data.username}' | base64 -d; echo
oc get secret mattermost-admin -n chat -o jsonpath='{.data.password}' | base64 -d; echo
```

### Grafana (dashboards)

```
echo "$GRAFANA_USER"
echo "$GRAFANA_PASSWORD"
```

### Keycloak (sign-in service)

```
echo "$KEYCLOAK_ADMIN_USER"
echo "$KEYCLOAK_ADMIN_PASSWORD"
```

### Argo CD (keeps the cluster matching Git)

The username is `admin`. Print the password:

```
oc get secret openshift-gitops-cluster -n openshift-gitops -o jsonpath='{.data.admin\.password}' | base64 -d; echo
```

### Loki (log search, no web page)

Loki has no sign-in page. Tools and commands that use it already have the details. To test it yourself:

```
curl -s --cacert "$LOKI_CA_FILE" -u "$LOKI_USER:$LOKI_PASSWORD" "$LOKI_URL/ready"
```

It prints `ready`.

## Step 3. Sign in

1. Paste the tool's address into your browser.
2. If the browser warns that the connection is not private, that is expected: the lab uses its own certificate. Choose **Advanced**, then continue to the site.
3. Type or paste the username and password from Step 2.

To copy a password from the terminal, select the line with your mouse and use your terminal's copy shortcut. Make sure you do not pick up spaces at the start or end.

## If something goes wrong

| What you see | What to do |
| --- | --- |
| `command not found: oc` | You are outside the lab shell. Run `lab shell`, then try again. |
| A command prints nothing | Run it again. If it still prints nothing, tell your instructor: the tool may still be starting. |
| The page says the password is wrong | Run the command again and copy the line carefully, with no spaces at either end. |
| The page does not open | Check that you copied the whole address, starting with `https://`. |

## Keep it private

- These passwords belong to your own lab only. Do not paste them into chat or share them.
- Your lab is deleted at the end of the day, and the passwords go with it.
