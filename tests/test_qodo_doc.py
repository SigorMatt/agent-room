import hashlib, os, subprocess, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ONELINER = ('import sys; t=open(sys.argv[1], encoding="utf-8").read(); '
            's=t.rsplit("<!-- BEGIN qodo_review.py -->",1)[1].rsplit("<!-- END qodo_review.py -->",1)[0]; '
            's=s.split("````python\\n",1)[1].rsplit("````",1)[0]; '
            'open(sys.argv[2],"w",encoding="utf-8").write(s)')


def extract(doc, out):
    subprocess.run([sys.executable, "-c", ONELINER, doc, out], check=True)
    with open(out, "rb") as f:
        data = f.read()
    compile(data, out, "exec")
    return hashlib.sha256(data).hexdigest()


class QodoDoc(unittest.TestCase):
    def test_appendix_matches_origin_main(self):
        r = subprocess.run(["git", "show", "origin/main:docs/QODO-REVIEW.md"],
                           cwd=ROOT, capture_output=True)
        if r.returncode != 0:
            self.skipTest("origin/main is missing; cannot compare the appendix")
        with tempfile.TemporaryDirectory() as d:
            ref = os.path.join(d, "ref.md")
            with open(ref, "wb") as f:
                f.write(r.stdout)
            a = extract(os.path.join(ROOT, "docs", "QODO-REVIEW.md"), os.path.join(d, "a.py"))
            b = extract(ref, os.path.join(d, "b.py"))
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
