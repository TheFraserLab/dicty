""" Combine pseudo p-values from stalks and spores

I am not putting too much stock in the FET p-values as meaningful, so instead I
use a pseudo p-value, which just takes the rank in the list (normalized by the
number of SNPs) and treats that as a p-value.  This automatically fulfills
assumptions of Fisher's method, which assumes only that the p-values input are
drawn from a uniform distribution.


"""
import pandas as pd
from os import path
from numpy import arange, log10
from argparse import ArgumentParser
from scipy.stats import combine_pvalues
from matplotlib.pyplot import (
    xlim,
    ylim,
    xticks,
    yticks,
    plot,
    scatter,
    xlabel,
    ylabel,
    legend,
    savefig,
    figure,
    subplot,
    close,
    title,
    tight_layout,
)
from numpy.random import shuffle, rand
from tqdm import tqdm


def parse_args():
    "Program specific argument parsing"
    parser = ArgumentParser()
    parser.add_argument("--output-prefix", "-o")
    parser.add_argument("--num-subplots", type=int, default=16)
    parser.add_argument("scores", nargs="+")

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    outdir = path.dirname(args.output_prefix)

    pvals_to_combine_fwd = {}
    pvals_to_combine_rev = {}
    pvals_to_combine_rand = {}

    fet_data = {}

    for file in tqdm(args.scores):
        fet_file = pd.read_table(file, squeeze=True, index_col=0)
        fet_pvals = fet_file.pval.copy()
        fet_pvals[
            (fet_file.stalk_alt + fet_file.spore_alt == 0)
            | (fet_file.stalk_ref + fet_file.spore_ref == 0)
        ] = pd.np.nan

        n = len(fet_pvals)
        fet_pvals_jitter = (fet_pvals + .01 * rand() * fet_pvals.min()).sort_index()

        expected = arange(1, n + 1) / fet_pvals.count() * pd.np.sign(fet_pvals)
        semi_ps = fet_file['rank'] / fet_file.maxrank
        semi_ps_rand = semi_ps.copy()
        shuffle(semi_ps_rand)
        fet_data[file] = fet_file.sort_index()
        pvals_to_combine_fwd[file] = semi_ps
        pvals_to_combine_rev[file] = 1 - semi_ps + 1 / fet_file['rank'].max()
        pvals_to_combine_rand[file] = semi_ps_rand

    pvals_to_combine_fwd = pd.DataFrame(pvals_to_combine_fwd)
    pvals_to_combine_rev = pd.DataFrame(pvals_to_combine_rev)
    pvals_to_combine_rand = pd.DataFrame(pvals_to_combine_rand)

    combined_pvals_fwd = pd.Series(index=pvals_to_combine_fwd.index, data=0.0)
    combined_pvals_rev = pd.Series(index=pvals_to_combine_rev.index, data=0.0)
    combined_pvals_rand = pd.Series(index=pvals_to_combine_rev.index, data=0.0)

    for ix in tqdm(combined_pvals_fwd.index):
        # Multiply by two to correct for testing both ends
        combined_pvals_fwd[ix] = (
            combine_pvalues(pvals_to_combine_fwd.loc[ix].dropna(), method="fisher") * 2
        )[1]
        combined_pvals_rev[ix] = (
            combine_pvalues(pvals_to_combine_rev.loc[ix].dropna(), method="fisher") * 2
        )[1]

        combined_pvals_rand[ix] = (
            combine_pvalues(pvals_to_combine_rand.loc[ix].dropna(), method="fisher") * 2
        )[1]

    combined_pvals_fwd.sort_values(inplace=True)
    combined_pvals_rev.sort_values(inplace=True)
    combined_pvals_rand.sort_values(inplace=True)

    combined_pvals_fwd.to_csv(args.output_prefix + ".Stalk.tsv", sep="\t")
    combined_pvals_rev.to_csv(args.output_prefix + ".Spore.tsv", sep="\t")

    figure()
    scatter(
        -log10(combined_pvals_rand), -log10(combined_pvals_fwd), label="Spore specific"
    )
    scatter(
        -log10(combined_pvals_rand), -log10(combined_pvals_rev), label="Stalk specific"
    )

    plot([0, 7], [0, 7], "r:")
    xlabel("Expected")
    ylabel("Observed")
    legend(loc="lower right")
    savefig(path.join(outdir, "combined_pvals_fwd_and_rev.png"))
    close()

    n_rows = int(pd.np.ceil(pd.np.sqrt(args.num_subplots)))
    n_cols = args.num_subplots // n_rows
    assert n_rows * n_cols >= args.num_subplots

    for name, dataset in (
        ("spore", combined_pvals_fwd),
        ("stalk", combined_pvals_rev),
        ("random", combined_pvals_rand),
    ):
        figure(figsize=(16, 12))

        for i in range(args.num_subplots):
            snp = dataset.index[i]
            ax = subplot(n_rows, n_cols, i + 1)
            title(
                "{}\n{} samples - {:3.1e}".format(
                    snp, len(pvals_to_combine_fwd.loc[snp].dropna()), dataset.loc[snp]
                )
            )
            stalks = [
                fet_data[file].loc[snp, "stalk_ratio"]
                for file in args.scores
                if (
                    fet_data[file].loc[snp, "stalk_alt"]
                    + fet_data[file].loc[snp, "spore_alt"]
                )
                > 0
            ]
            spores = [
                fet_data[file].loc[snp, "spore_ratio"]
                for file in args.scores
                if (
                    fet_data[file].loc[snp, "stalk_alt"]
                    + fet_data[file].loc[snp, "spore_alt"]
                )
                > 0
            ]
            scatter(stalks, spores)
            plot([0, 1], [0, 1], "r:")
            ax.set_aspect(1)
            xlim(-0.1, 1.1)
            ylim(-0.1, 1.1)
            if i % n_cols == 0:
                ylabel("Spores")
                yticks([0, .25, .5, .75, 1])
            else:
                yticks([])
            if i // n_cols == n_rows - 1:
                xlabel("Stalks")
                xticks([0, .5, 1])
            else:
                xticks([])

        tight_layout()
        savefig(path.join(outdir, "{}_snps.png".format(name)))
        close()
