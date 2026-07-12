import re
with open('config/agent_network.json', 'r') as f:
    c = f.read()

# There are multiple conflict markers because git rebase/merge left them
# Let's completely clean up config/agent_network.json based on what we had done before.
