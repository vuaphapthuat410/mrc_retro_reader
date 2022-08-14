# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import collections
import json
from evaluate_squad import squad_evaluate
from data_utils import get_examples


def get_score1(cof, best_cof, args, examples):
    all_scores = collections.OrderedDict()
    idx = 0
    for input_file in args.input_null_files.split(","):
        with open(input_file, 'r') as reader:
            input_data = json.load(reader, strict=False)
            for (key, score) in input_data.items():
                if key not in all_scores:
                    all_scores[key] = []
                all_scores[key].append(cof[idx] * score)
        idx += 1
    output_scores = {}
    for (key, scores) in all_scores.items():
        mean_score = 0.0
        for score in scores:
            mean_score += score
        mean_score /= float(len(scores))
        output_scores[key] = mean_score

    idx = 0
    all_nbest = collections.OrderedDict()
    for input_file in args.input_nbest_files.split(","):
        with open(input_file, "r") as reader:
            input_data = json.load(reader, strict=False)
            for (key, entries) in input_data.items():
                if key not in all_nbest:
                    all_nbest[key] = collections.defaultdict(float)
                for entry in entries:
                    all_nbest[key][entry["text"]] += best_cof[idx] * entry["probability"]
        idx += 1
    output_predictions = {}
    for (key, entry_map) in all_nbest.items():
        null_score = output_scores[key]
        if null_score > args.null_score_diff_threshold:
            output_predictions[key] = ""
        else:
            sorted_texts = sorted(
                entry_map.keys(), key=lambda x: entry_map[x], reverse=True)
            best_text = sorted_texts[0]
            output_predictions[key] = best_text
    if args.predict_test:
        with open("results.json", "w") as f:
            json.dump(output_predictions, f, indent= 4)
        return output_predictions
    elif args.predict_pri_test:
        with open("pri_results.json", "w") as f:
            json.dump(output_predictions, f, indent= 4)
        return output_predictions
    else:
        with open("valid_predictions.json", "w") as f:
            json.dump(output_predictions, f, indent= 4)
            
    eval_score = squad_evaluate(examples, output_predictions, output_scores,
                            args.null_score_diff_threshold)
    return eval_score


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument('--input_null_files', type=str, default=
    "cls_score.json,ensemble/model1/null_odds.json,ensemble/model2/null_odds.json,ensemble/model3/null_odds.json")

    parser.add_argument('--input_nbest_files', type=str, default="ensemble/model1/nbest_predictions.json,ensemble/model2/nbest_predictions.json,ensemble/model3/nbest_predictions.json"
                        )

    parser.add_argument('--null_score_diff_threshold',
                        type=float, default=0,
                        help="If null_score - best_non_null is greater than the threshold predict null.")
    parser.add_argument("--predict_file", default="dev-v2.0.json")
    parser.add_argument("--v2", default=False, action='store_true', help="Whether to run training.")
    parser.add_argument('--fin_cof', type=str, default= None)
    parser.add_argument('--fin_best_cof', type=str, default= None)
    parser.add_argument("--predict_test", default=False, action='store_true', help="Whether to test.")
    parser.add_argument("--predict_pri_test", default=False, action='store_true', help="private test is in used.")
    parser.add_argument('--start', type=int, default= 100)
    parser.add_argument('--start_cof', type=int, default= 100)

    args = parser.parse_args()
    print("Null files")
    for null_file in args.input_null_files.split(","):
        print(null_file)
    print("Nbest files")
    for null_file in args.input_nbest_files.split(","):
        print(null_file)
    
    examples = get_examples(args.predict_file, is_training= False)
    
    if args.fin_cof is None:
        fin_cof = None
        best_score = 0.
        fin_best_cof = None
        for C1 in range(args.start, -1, -10):
            for C2 in range(0, (100 - C1) + 1, 10):
                for C3 in range(0, (100 - C1 - C2) + 1, 10):
                    for C4 in range(0, (100 - C1 - C2 - C3) + 1, 10):
                        for C5 in range(0, (100 - C1 - C2 - C3 - C4) + 1, 10):
                            C6 = 100 - C1 - C2 - C3 - C4 - C5
                            c1 = float(C1) / 100.
                            c2 = float(C2) / 100.
                            c3 = float(C3) / 100.
                            c4 = float(C4) / 100.
                            c5 = float(C5) / 100.
                            c6 = float(C6) / 100.

                            cof = [c1, c2, c3, c4, c5, c6]
                            best_cof = [1, 1, 1, 1, 1, 1]
                            scores = get_score1(cof, best_cof, args, examples)
                            score = scores['best_f1']
                            if score > best_score:
                                best_score = score
                                fin_cof = cof
                                fin_best_cof = best_cof
                            print("cur_score", score, "\t", cof, "\t", best_cof,"\t", "cur_best", best_score, "\t", fin_cof,
                                  "\t", fin_best_cof)
    else:
        fin_cof = [float(x.strip()) for x in args.fin_cof.split(",")]

    if args.fin_best_cof is None:
        best_score = 0.
        best_thresh = 0.
        fin_best_cof = None

        for C1 in range(args.start_cof, -1, -5):
            for C2 in range(0, (100 - C1) + 1, 5):
                for C3 in range(0, (100 - C2 - C1) + 1, 5):
                    C4 = 100 - C1 - C2 - C3
                    c1 = float(C1)/100.
                    c2 = float(C2)/100.
                    c3 = float(C3)/100.
                    c4 = float(C4)/100.

                    cof = fin_cof
                    best_cof = [c1, c2, c3, c4]
                    scores = get_score1(cof, best_cof, args, examples)
                    score = scores['best_f1']
                    if score > best_score:
                        best_score = score
                        best_thresh = scores['best_f1_thresh']
                        fin_cof = cof
                        fin_best_cof=best_cof
                    print("cur_score", score, "\t", cof, "\t", best_cof, "\t","cur_best", best_score, "\t", fin_cof, "\t", fin_best_cof)
    else:
        fin_best_cof = [float(x.strip()) for x in args.fin_best_cof.split(",")]
    
    scores = get_score1(fin_cof, fin_best_cof, args, examples)
    print(json.dumps(scores, indent= 4, ensure_ascii=False))
    # print("\nbest", best_score, "thresh", best_thresh, "\t", fin_cof, "\t", fin_best_cof)

if __name__ == "__main__":
    main()