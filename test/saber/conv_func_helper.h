/* Copyright (c) 2018 Anakin Authors, Inc. All Rights Reserved.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/

#ifndef ANAKIN_CONV_FUNC_HELPER_H
#define ANAKIN_CONV_FUNC_HELPER_H

#include "omp.h"
#include "saber/core/tensor.h"

namespace anakin {
namespace saber {

template<typename targetType>
void conv_basic_check(Tensor<targetType> &tensor_in,Tensor<targetType> &tensor_out,
                      const float *weights, const float *bias, int group,
                      int kernel_w, int kernel_h, int stride_w, int stride_h, int dilation_w, int dilation_h,
                      int pad_w, int pad_h, bool flag_bias, bool flag_relu) {

    auto src_data = reinterpret_cast<const float*>(tensor_in.data());
    auto dst_data_ref = reinterpret_cast<float*>(tensor_out.mutable_data());
    auto weights_data = weights;
    bool with_bias = flag_bias;
    auto bias_data = bias;

    int in_num = tensor_out.num();
    int out_channels = tensor_out.channel();
    int out_h = tensor_out.height();
    int out_w = tensor_out.width();

    int in_channel = tensor_in.channel();
    int in_h = tensor_in.height();
    int in_w = tensor_in.width();
    int out_c_group = out_channels / group;
    int in_c_group = in_channel / group;

#pragma omp parallel for num_threads(40) collapse(5) schedule(static)
    for (int n = 0; n < in_num; ++n) {
        for (int g = 0; g < group; ++g) {
            for (int oc = 0; oc < out_c_group; ++oc) {
                for (int oh = 0; oh < out_h; ++oh) {
                    for (int ow = 0; ow < out_w; ++ow) {
                        int out_idx = n * group * out_c_group * out_h * out_w + g * out_c_group * out_h * out_w
                                   + oc * out_h * out_w + oh * out_w + ow;
                        dst_data_ref[out_idx] = with_bias ? (float)(bias_data[g * out_c_group + oc]) : 0.f;

                        for (int ic = 0; ic < in_c_group; ++ic) {
                            for (int kh = 0; kh < kernel_h; ++kh) {
                                for (int kw = 0; kw < kernel_w; ++kw) {
                                    int iw = ow * stride_w - pad_w + kw * (1 + dilation_h);
                                    int ih = oh * stride_h - pad_h + kh * (1 + dilation_w);
                                    if (iw < 0 || iw >= in_w) continue;
                                    if (ih < 0 || ih >= in_h) continue;

                                    int iidx = n * in_channel * in_h * in_w
                                               + g * in_c_group * in_h * in_w
                                               + ic * in_h * in_w
                                               + ih * in_w
                                               + iw;
                                    int widx = g * out_c_group * in_c_group * kernel_h * kernel_w
                                               + oc * in_c_group * kernel_h * kernel_w
                                               + ic * kernel_h * kernel_w
                                               + kh * kernel_w
                                               + kw;

                                    dst_data_ref[out_idx]
                                            += src_data[iidx]
                                               * weights_data[widx];
                                }
                            }
                        }

                        if (flag_relu) {
                            dst_data_ref[out_idx] = dst_data_ref[out_idx] > 0.f ? dst_data_ref[out_idx] : 0.f;
                        }
                    }
                }
            }
        }
    }
}
}
}
#endif //ANAKIN_CONV_FUNC_HELPER_H
