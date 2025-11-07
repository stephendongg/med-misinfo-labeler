# CDA Approved Drugs Labeler 
## Note:
- Bookmark this tab for ease of access. 

## Quick Links:
Project Sepctific
- [Project Repo](https://drive.google.com/drive/u/0/folders/1jaiOBhk-5XAITQL_i_6qKUUg01tlnjVd)
- [Assignment Doc](https://docs.google.com/document/d/1rQrgdzop-6PgfUXK8_p0n2VOfUJENYwo3zitkWgu_rY/edit?tab=t.jl6mduu0sudz)
- [Policy Proposal](https://docs.google.com/document/d/1f-2VSGjHfFOUZXSHIMBSCVEWm4NRnzjaj4kAB7C3mjw/edit?tab=t.jzvd2wwrer9s)
- [LucidChart](https://lucid.app/lucidspark/c4ef53c4-81c8-4e82-bd4e-80c468ec0148/edit?viewport_loc=-27%2C-291%2C1719%2C1040%2C0_0&invitationId=inv_5d69265f-11e1-48a0-b335-54c276ce259c)
Technical Documentation
- [AT Protocol SDK](https://atproto.blue/en/latest/).


## Automated labeler
The bulk of your Part I implementation will be in `automated_labeler.py`. You are
welcome to modify this implementation as you wish. However, you **must**
preserve the signatures of the `__init__` and `moderate_post` functions,
otherwise the testing/grading script will not work. You may also use the
functions defined in `label.py`. You can import them like so:
```
from .label import post_from_url
```

For Part II, you will create a file called `policy_proposal_labeler.py` for your
implementation. You are welcome to create additional files as you see fit.

## Input files
For Part I, your labeler will have as input lists of T&S words/domains, news
domains, and a list of dog pictures. These inputs can be found in the
`labeler-inputs` directory. For testing, we have CSV files where the rows
consist of URLs paired with the expected labeler output. These can be found
under the `test-data` directory.

## Testing
We provide a testing harness in `test-labeler.py`. To test your labeler on the
input posts for dog pictures, you can run the following command and expect to
see the following output:

```
% python test_labeler.py labeler-inputs test-data/input-posts-dogs.csv
The labeler produced 20 correct labels assignments out of 20
Overall ratio of correct label assignments 1.0
```

